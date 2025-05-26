import os
import logging
from utils.git_helpers import pull_updates, GitPullFailedError

logger = logging.getLogger(__name__)

class RepositoryServiceError(Exception):
    """Custom exception for repository service errors."""
    pass

class RepositoryService:
    def __init__(self, base_repo_path: str):
        self.base_repo_path = os.path.abspath(base_repo_path) # Normalize path
        if not os.path.isdir(self.base_repo_path):
            logger.error(f"Base repository path '{self.base_repo_path}' is not a valid directory.")
            # Depending on application design, this could raise an error immediately
            # or allow instantiation and fail on operations.
            # For robustness, failing early is often better.
            raise ValueError(f"Base repository path '{self.base_repo_path}' is not a valid directory.")

    def _sanitize_repo_name(self, repo_name: str) -> str:
        """Basic sanitization for repository name to prevent path traversal."""
        # Disallow directory traversal components
        if ".." in repo_name or os.path.isabs(repo_name):
            raise ValueError("Invalid repository name: contains '..' or is an absolute path.")
        # Further sanitization might be needed depending on OS and filesystem specifics
        # (e.g., disallowing special characters, checking length, etc.)
        return repo_name

    def update_repository(self, repo_name: str) -> dict:
        """
        Updates a specific repository by pulling the latest changes.

        Args:
            repo_name: The name of the repository (subdirectory within base_repo_path).

        Returns:
            A dictionary with status and git output upon success.

        Raises:
            RepositoryServiceError: If any error occurs during the process.
            ValueError: If repo_name is invalid.
        """
        try:
            sane_repo_name = self._sanitize_repo_name(repo_name)
        except ValueError as ve:
            logger.error(f"Invalid repository name provided: '{repo_name}'. Error: {str(ve)}")
            raise RepositoryServiceError(f"Invalid repository name '{repo_name}': {str(ve)}")

        repo_path = os.path.join(self.base_repo_path, sane_repo_name)
        
        # Double check that the resolved path is within the base_repo_path (defense in depth)
        if not os.path.abspath(repo_path).startswith(self.base_repo_path):
            logger.error(f"Path traversal attempt detected for repo_name '{repo_name}'. Resolved path '{os.path.abspath(repo_path)}' is outside base '{self.base_repo_path}'.")
            raise RepositoryServiceError(f"Invalid repository path for '{repo_name}'.")

        logger.info(f"Attempting to update repository: {repo_path}")

        try:
            output = pull_updates(repo_path)
            logger.info(f"Repository '{repo_name}' updated successfully via pull_updates.")
            return {"status": "success", "output": output if output else "No new output from git pull."}
        
        except GitPullFailedError as e:
            # str(e) from GitPullFailedError is already detailed.
            logger.error(f"Failed to update repository '{repo_name}' due to GitPullFailedError: {str(e)}")
            # Wrap in RepositoryServiceError as per pattern, including the detailed message from GitPullFailedError.
            raise RepositoryServiceError(f"Error processing repository '{repo_name}': {str(e)}")
        
        except Exception as e:
            # Catch any other unexpected errors.
            logger.exception(f"An unexpected error occurred while updating repository '{repo_name}'.")
            raise RepositoryServiceError(f"Unexpected error processing repository '{repo_name}': {str(e)}")

# Example (for testing or direct script use, typically not part of a service file like this)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO,
#                         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     
#     # Ensure this path exists and is a directory where you can create test repos
#     # e.g., mkdir /tmp/my_repos
#     # Then, inside /tmp/my_repos:
#     # mkdir test_repo1 && cd test_repo1 && git init && git commit --allow-empty -m "Initial" && cd ..
#     # mkdir test_repo_nodir # This one won't be a git repo or might not exist
# 
#     try:
#         service = RepositoryService(base_repo_path="/tmp/my_repos")
#     except ValueError as e:
#         logger.error(f"Failed to initialize RepositoryService: {e}")
#         exit(1)
# 
#     # Test case 1: Valid repository
#     try:
#         logger.info("--- Test Case 1: Updating valid repository 'test_repo1' ---")
#         result = service.update_repository("test_repo1")
#         logger.info(f"Update result for 'test_repo1': {result}")
#     except RepositoryServiceError as e:
#         logger.error(f"Service error for 'test_repo1': {str(e)}")
# 
#     # Test case 2: Non-existent repository directory (but valid name format)
#     try:
#         logger.info("--- Test Case 2: Updating non-existent repository 'test_repo_nodir' ---")
#         result = service.update_repository("test_repo_nodir") # pull_updates should handle this
#         logger.info(f"Update result for 'test_repo_nodir': {result}")
#     except RepositoryServiceError as e:
#         logger.error(f"Service error for 'test_repo_nodir': {str(e)}")
# 
#     # Test case 3: Invalid repository name (path traversal attempt)
#     try:
#         logger.info("--- Test Case 3: Updating with invalid name '../outside_repo' ---")
#         result = service.update_repository("../outside_repo")
#         logger.info(f"Update result for '../outside_repo': {result}")
#     except RepositoryServiceError as e:
#         logger.error(f"Service error for '../outside_repo': {str(e)}")
#     except ValueError as e: # If _sanitize_repo_name raises ValueError directly
#         logger.error(f"ValueError for '../outside_repo': {str(e)}")
#
#     # Test case 4: Assuming git is not installed (manual test)
#     # To test this, you'd need to run in an environment where 'git' is not in PATH.
#     # logger.info("--- Test Case 4: Git command not found (requires manual PATH adjustment) ---")
#     # try:
#     #     result = service.update_repository("test_repo1") # Assuming test_repo1 exists
#     # except RepositoryServiceError as e:
#     #     logger.error(f"Service error for 'test_repo1' (git not found test): {str(e)}")
