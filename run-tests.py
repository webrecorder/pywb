import pytest
result = pytest.main('-v --doctest-module tests/ pywb/')
exit(result)
