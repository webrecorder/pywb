def pytest_configure(config):
    import sys
    sys._called_from_test = True
