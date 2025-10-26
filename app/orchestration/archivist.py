from google.cloud import firestore
from .models import Job
import logging

logger = logging.getLogger("llmhive")

class Archivist:
    """
    The Archivist. It handles all interactions with the Firestore database,
    saving and retrieving "Case Files" (Jobs).
    """
    def __init__(self):
        # The client will automatically use the project's credentials
        # and project ID from the Cloud Run environment.
        self.db = firestore.Client()
        self.collection_name = "jobs"
        logger.info("Archivist initialized, connected to Firestore.")

    def save_job(self, job: Job):
        """Saves a completed or failed job to the database."""
        try:
            # The document ID in Firestore will be our unique Job ID.
            doc_ref = self.db.collection(self.collection_name).document(job.id)
            
            # We save the entire Job object, converted to a dictionary.
            # The `mode='json'` argument ensures enums and other types are serialized correctly.
            doc_ref.set(job.model_dump(mode='json'))
            logger.info(f"Archivist saved Job ID: {job.id} to Firestore.")
        except Exception as e:
            # We log the error but do not raise it. Failing to save a job
            # is a non-critical error that should not crash the main application.
            logger.error(f"Archivist failed to save Job ID: {job.id}. Error: {e}", exc_info=True)
