"""
Main test runner for Startup Finder.
"""
import unittest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests.test_functionality import TestStartupFinder
from tests.test_integration import TestSystemIntegration

if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestStartupFinder))
    
    # Add integration tests only if not explicitly skipped
    if not os.environ.get("SKIP_INTEGRATION_TESTS"):
        test_suite.addTest(unittest.makeSuite(TestSystemIntegration))
    else:
        print("Skipping integration tests that require web access")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with non-zero code if tests failed
    sys.exit(not result.wasSuccessful())
