"""NZB password extraction plugin."""

import pathlib
import re
import xml.etree.ElementTree as ET

from .password_plugin import PasswordPlugin


class NzbPasswordPlugin(PasswordPlugin):
    """Plugin to extract passwords from NZB filenames with {{password}} format."""
    
    def can_handle(self, file_path: pathlib.Path) -> bool:
        """Check if this is an NZB file."""
        return file_path.suffix.lower() == '.nzb'
    
    def extract_passwords(self, file_path: pathlib.Path) -> dict[str, set[str]]:
        """Extract password from filename with {{password}} pattern."""
        filename = file_path.stem
        
        password_matches = re.findall(r'\{\{(.+?)\}\}', filename)
        
        if not password_matches:
            return {}
        
        title = re.sub(r'\{\{.+?\}\}', '', filename).strip()
        
        if not title:
            title = filename
        
        return {title: set(password_matches)}