import pytest
from app.scratchpad import Scratchpad


def test_scratchpad_add_entry():
    """Test adding an entry to the scratchpad."""
    scratchpad = Scratchpad()
    scratchpad.add_entry("key1", "value1")
    assert scratchpad.get_entry("key1") == "value1"


def test_scratchpad_get_entry():
    """Test retrieving an entry from the scratchpad."""
    scratchpad = Scratchpad()
    scratchpad.add_entry("key1", "value1")
    scratchpad.add_entry("key2", {"nested": "data"})
    
    assert scratchpad.get_entry("key1") == "value1"
    assert scratchpad.get_entry("key2") == {"nested": "data"}
    assert scratchpad.get_entry("nonexistent") is None


def test_scratchpad_clear():
    """Test clearing the scratchpad."""
    scratchpad = Scratchpad()
    scratchpad.add_entry("key1", "value1")
    scratchpad.add_entry("key2", "value2")
    
    scratchpad.clear()
    
    assert scratchpad.get_entry("key1") is None
    assert scratchpad.get_entry("key2") is None
