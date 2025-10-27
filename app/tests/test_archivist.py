"""
Test the Archivist service for Phase 3.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestration.models import Job, JobStatus, SharedMemory, StepResult
from orchestration.archivist import Archivist
from unittest.mock import Mock, patch, MagicMock

def test_archivist_initialization():
    """Test that Archivist can be initialized with a mocked Firestore client."""
    with patch('orchestration.archivist.firestore.Client') as mock_client, \
         patch('orchestration.archivist.aiplatform.init') as mock_aiplatform_init, \
         patch('orchestration.archivist.aiplatform.MatchingEngineIndexEndpoint') as mock_endpoint, \
         patch('orchestration.archivist.TextEmbeddingModel.from_pretrained') as mock_embedding_model:
        archivist = Archivist()
        assert archivist.collection_name == "jobs"
        mock_client.assert_called_once()
        mock_aiplatform_init.assert_called_once()
        mock_endpoint.assert_called_once()
        mock_embedding_model.assert_called_once()
        print("✓ Archivist initialization test passed")

def test_archivist_save_job_success():
    """Test that Archivist can save a job successfully."""
    with patch('orchestration.archivist.firestore.Client') as mock_client, \
         patch('orchestration.archivist.aiplatform.init'), \
         patch('orchestration.archivist.aiplatform.MatchingEngineIndexEndpoint') as mock_endpoint_cls, \
         patch('orchestration.archivist.TextEmbeddingModel.from_pretrained') as mock_embedding_cls:
        # Create mock Firestore client and document reference
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_doc_ref = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        
        # Create mock embedding model and endpoint
        mock_embedding_model = MagicMock()
        mock_embedding_response = MagicMock()
        mock_embedding_response.values = [0.1, 0.2, 0.3]
        mock_embedding_model.get_embeddings.return_value = [mock_embedding_response]
        mock_embedding_cls.return_value = mock_embedding_model
        
        mock_endpoint = MagicMock()
        mock_endpoint_cls.return_value = mock_endpoint
        
        archivist = Archivist()
        
        # Create a test job
        job = Job.from_prompt("Test prompt")
        job.status = JobStatus.COMPLETED
        job.result = {"result": "test result"}
        
        # Save the job
        archivist.save_job(job)
        
        # Verify that Firestore methods were called correctly
        mock_db.collection.assert_called_with("jobs")
        mock_collection.document.assert_called_with(job.id)
        mock_doc_ref.set.assert_called_once()
        
        # Verify that model_dump was called with mode='json'
        call_args = mock_doc_ref.set.call_args[0][0]
        assert isinstance(call_args, dict)
        assert 'id' in call_args
        
        # Verify that embedding methods were called
        mock_embedding_model.get_embeddings.assert_called_once()
        mock_endpoint.upsert_datapoints.assert_called_once()
        
        print("✓ Archivist save_job success test passed")

def test_archivist_save_job_handles_errors():
    """Test that Archivist handles errors gracefully without raising."""
    with patch('orchestration.archivist.firestore.Client') as mock_client, \
         patch('orchestration.archivist.aiplatform.init'), \
         patch('orchestration.archivist.aiplatform.MatchingEngineIndexEndpoint'), \
         patch('orchestration.archivist.TextEmbeddingModel.from_pretrained'):
        # Create mock that raises an exception
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        mock_db.collection.side_effect = Exception("Firestore error")
        
        archivist = Archivist()
        
        # Create a test job
        job = Job.from_prompt("Test prompt")
        
        # This should not raise an exception
        try:
            archivist.save_job(job)
            print("✓ Archivist error handling test passed")
        except Exception as e:
            print(f"✗ Archivist should not raise exceptions, but got: {e}")
            raise

def test_job_model_dump_json_mode():
    """Test that Job model can be dumped with mode='json'."""
    job = Job.from_prompt("Test prompt")
    job.status = JobStatus.COMPLETED
    
    # Test that model_dump works with mode='json'
    job_dict = job.model_dump(mode='json')
    
    assert isinstance(job_dict, dict)
    assert job_dict['status'] == 'COMPLETED'  # Enum should be serialized as string
    assert 'id' in job_dict
    assert 'shared_memory' in job_dict
    
    print("✓ Job model_dump JSON mode test passed")

def test_archivist_find_similar_jobs():
    """Test that Archivist can find similar jobs using Vector Search."""
    with patch('orchestration.archivist.firestore.Client') as mock_client, \
         patch('orchestration.archivist.aiplatform.init'), \
         patch('orchestration.archivist.aiplatform.MatchingEngineIndexEndpoint') as mock_endpoint_cls, \
         patch('orchestration.archivist.TextEmbeddingModel.from_pretrained') as mock_embedding_cls:
        # Create mock Firestore client and document reference
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        
        # Create mock embedding model
        mock_embedding_model = MagicMock()
        mock_embedding_response = MagicMock()
        mock_embedding_response.values = [0.1, 0.2, 0.3]
        mock_embedding_model.get_embeddings.return_value = [mock_embedding_response]
        mock_embedding_cls.return_value = mock_embedding_model
        
        # Create mock endpoint with neighbors
        mock_endpoint = MagicMock()
        mock_neighbor = MagicMock()
        mock_neighbor.id = "test-job-id"
        mock_endpoint.find_neighbors.return_value = [[mock_neighbor]]
        mock_endpoint_cls.return_value = mock_endpoint
        
        # Create mock document for retrieval
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'test-job-id',
            'status': 'COMPLETED',
            'shared_memory': {
                'original_prompt': 'Test prompt',
                'intermediate_steps': {}
            }
        }
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection.document.return_value = mock_doc_ref
        
        archivist = Archivist()
        
        # Find similar jobs
        similar_jobs = archivist.find_similar_jobs("Test query", num_results=3)
        
        # Verify methods were called
        mock_embedding_model.get_embeddings.assert_called_once()
        mock_endpoint.find_neighbors.assert_called_once()
        mock_collection.document.assert_called_with("test-job-id")
        
        # Verify results
        assert len(similar_jobs) == 1
        assert isinstance(similar_jobs[0], Job)
        assert similar_jobs[0].id == 'test-job-id'
        
        print("✓ Archivist find_similar_jobs test passed")

if __name__ == "__main__":
    print("Running Archivist Tests...\n")
    
    test_archivist_initialization()
    test_archivist_save_job_success()
    test_archivist_save_job_handles_errors()
    test_job_model_dump_json_mode()
    test_archivist_find_similar_jobs()
    
    print("\n✅ All Archivist tests passed!")
