from __future__ import annotations

import logging
from types import SimpleNamespace

from .models import Job

try:  # Optional dependency: Firestore client
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover - handled by fallback behaviour
    firestore = SimpleNamespace(Client=None)  # type: ignore

try:  # Optional dependency: Vertex AI platform
    from google.cloud import aiplatform  # type: ignore
except Exception:  # pragma: no cover - handled by fallback behaviour
    aiplatform = SimpleNamespace(
        init=lambda *args, **kwargs: None,
        MatchingEngineIndexEndpoint=None,
    )  # type: ignore

try:  # Optional dependency: Vertex AI text embeddings
    from vertexai.language_models import TextEmbeddingModel  # type: ignore
except Exception:  # pragma: no cover - handled by fallback behaviour
    class _TextEmbeddingModelStub:  # pragma: no cover - testing stub
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            raise RuntimeError("Vertex AI embeddings are unavailable")

    TextEmbeddingModel = _TextEmbeddingModelStub  # type: ignore

logger = logging.getLogger("llmhive")

# --- Configuration for Vertex AI ---
PROJECT_ID = "llmhive-orchestrator"
REGION = "us-east1"
INDEX_ID = "llmhive-job-index"
ENDPOINT_ID = "llmhive-job-endpoint"
EMBEDDING_MODEL_NAME = "textembedding-gecko@003"
# ---


class Archivist:
    """Persist jobs and embeddings when cloud credentials are available.

    In development and local testing environments we often do not have
    Google Cloud credentials or the Vertex AI SDK installed.  Instead of
    raising an exception during service start-up, the Archivist now detects
    missing dependencies and gracefully degrades into a no-op implementation.
    """

    def __init__(self) -> None:
        self.db = None
        self.collection_name = "jobs"
        self.endpoint = None
        self.embedding_model = None
        self.enabled = False

        if not self._dependencies_available():
            logger.warning(
                "Archivist dependencies are unavailable. Running in no-op mode."
            )
            return

        try:
            # Firestore client for saving full job details
            self.db = firestore.Client()

            # Initialize Vertex AI client
            aiplatform.init(project=PROJECT_ID, location=REGION)

            # Get a reference to our deployed Vector Search endpoint
            self.endpoint = aiplatform.MatchingEngineIndexEndpoint(ENDPOINT_ID)

            # Get a reference to the Vertex AI text embedding model
            self.embedding_model = TextEmbeddingModel.from_pretrained(
                EMBEDDING_MODEL_NAME
            )

            self.enabled = True
            logger.info(
                "Archivist initialized, connected to Firestore and Vertex AI Embedding Service."
            )
        except Exception as exc:  # pragma: no cover - requires cloud services
            logger.warning(
                "Archivist could not initialize cloud backends and will run in no-op mode: %s",
                exc,
            )
            self.db = None
            self.endpoint = None
            self.embedding_model = None
            self.enabled = False

    def _get_embedding(self, text: str) -> list[float]:
        """Generates an embedding for a given text using the Vertex AI API."""
        if not (self.enabled and self.embedding_model):
            raise RuntimeError("Embedding model is not available")

        response = self.embedding_model.get_embeddings([text])
        return response[0].values

    @staticmethod
    def _dependencies_available() -> bool:
        """Check at runtime whether Firestore and Vertex AI clients are available."""

        has_firestore = getattr(firestore, "Client", None) is not None
        has_endpoint = getattr(aiplatform, "MatchingEngineIndexEndpoint", None) is not None
        embedding_ctor = getattr(TextEmbeddingModel, "from_pretrained", None)
        return has_firestore and has_endpoint and callable(embedding_ctor)

    def save_job(self, job: Job):
        """Saves a job to Firestore and its embedding to Vector Search."""
        if not self.enabled:
            logger.debug(
                "Archivist.save_job skipped because cloud backends are disabled."
            )
            return

        try:
            # 1. Save the full job object to Firestore
            doc_ref = self.db.collection(self.collection_name).document(job.id)
            doc_ref.set(job.model_dump(mode='json'))
            logger.info(f"Archivist saved Job ID: {job.id} to Firestore.")

            # 2. Create a vector embedding from the original prompt via API call
            prompt_text = job.shared_memory.original_prompt
            embedding = self._get_embedding(prompt_text)
            
            # 3. Save the embedding to Vertex AI Vector Search
            self.endpoint.upsert_datapoints(
                datapoints=[{"datapoint_id": job.id, "feature_vector": embedding}]
            )
            logger.info(f"Archivist saved embedding for Job ID: {job.id} to Vector Search.")

        except Exception as e:
            logger.error(
                f"Archivist failed to save Job ID: {job.id}. Error: {e}",
                exc_info=True,
            )

    def find_similar_jobs(self, prompt: str, num_results: int = 3) -> list[Job]:
        """Finds similar past jobs using Vector Search."""
        if not self.enabled:
            logger.debug(
                "Archivist.find_similar_jobs skipped because cloud backends are disabled."
            )
            return []

        try:
            # 1. Create an embedding for the new prompt via API call
            query_embedding = self._get_embedding(prompt)

            # 2. Query the Vector Search endpoint to find nearest neighbors
            response = self.endpoint.find_neighbors(
                queries=[query_embedding],
                num_neighbors=num_results
            )
            logger.info(f"Archivist found {len(response[0])} potential similar jobs.")

            # 3. Retrieve the full job details from Firestore
            similar_jobs = []
            for neighbor in response[0]:
                job_id = neighbor.id
                doc_ref = self.db.collection(self.collection_name).document(job_id)
                doc = doc_ref.get()
                if doc.exists:
                    similar_jobs.append(Job(**doc.to_dict()))
            
            logger.info(f"Archivist retrieved {len(similar_jobs)} full jobs from Firestore.")
            return similar_jobs
        except Exception as e:
            logger.error(
                f"Archivist failed to find similar jobs. Error: {e}",
                exc_info=True,
            )
            return []  # Return an empty list on failure
