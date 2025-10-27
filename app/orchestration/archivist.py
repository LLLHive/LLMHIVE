from google.cloud import firestore
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from .models import Job
import logging
import os

logger = logging.getLogger("llmhive")

# --- Configuration for Vertex AI ---
PROJECT_ID = "llmhive-orchestrator"
REGION = "us-east1"
INDEX_ID = "llmhive-job-index"
ENDPOINT_ID = "llmhive-job-endpoint"
EMBEDDING_MODEL_NAME = "textembedding-gecko@003"
# ---

class Archivist:
    """
    The Archivist. It handles all interactions with Firestore (long-term memory)
    and Vertex AI Vector Search (semantic memory), using the native Vertex AI embedding model.
    """
    def __init__(self):
        # Firestore client for saving full job details
        self.db = firestore.Client()
        self.collection_name = "jobs"
        
        # Initialize Vertex AI client
        aiplatform.init(project=PROJECT_ID, location=REGION)
        
        # Get a reference to our deployed Vector Search endpoint
        self.endpoint = aiplatform.MatchingEngineIndexEndpoint(ENDPOINT_ID)

        # Get a reference to the Vertex AI text embedding model
        self.embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
        
        logger.info("Archivist initialized, connected to Firestore and Vertex AI Embedding Service.")

    def _get_embedding(self, text: str) -> list[float]:
        """Generates an embedding for a given text using the Vertex AI API."""
        response = self.embedding_model.get_embeddings([text])
        return response[0].values

    def save_job(self, job: Job):
        """Saves a job to Firestore and its embedding to Vector Search."""
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
            logger.error(f"Archivist failed to save Job ID: {job.id}. Error: {e}", exc_info=True)

    def find_similar_jobs(self, prompt: str, num_results: int = 3) -> list[Job]:
        """Finds similar past jobs using Vector Search."""
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
            logger.error(f"Archivist failed to find similar jobs. Error: {e}", exc_info=True)
            return [] # Return an empty list on failure
