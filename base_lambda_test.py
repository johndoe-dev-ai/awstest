import pytest

class BaseLambdaTest:
    @pytest.fixture(autouse=True)
    def setup(self, aws_services):
        self.aws_services = aws_services

    def setup_test_data(self):
        """
        Override this method in the specific test class to set up any necessary test data.
        """
        pass

    def test_lambda_handler_success(self):
        """
        Override this method in the specific test class to test the success case.
        """
        pass

    def test_lambda_handler_error(self):
        """
        Override this method in the specific test class to test the error case.
        """
        pass
