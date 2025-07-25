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
        """Extract passwords from filename and NZB file content."""
        filename = file_path.stem
        passwords = set()
        
        # Extract from filename {{password}} pattern
        filename_passwords = re.findall(r'\{\{(.+?)\}\}', filename)
        passwords.update(filename_passwords)
        
        # Extract from XML content <meta type="password">
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse XML with NZB namespace
            root = ET.fromstring(content)
            ns = {'nzb': 'http://www.newzbin.com/DTD/2003/nzb'}
            
            for meta in root.findall('.//nzb:meta[@type="password"]', ns):
                if meta.text:
                    passwords.add(meta.text.strip())
        except (ET.ParseError, OSError, UnicodeDecodeError):
            # If XML parsing fails, continue with filename-only extraction
            pass
        
        if not passwords:
            return {}
        
        # Create title by removing password patterns from filename
        title = re.sub(r'\{\{.+?\}\}', '', filename).strip()
        
        if not title:
            title = filename
        
        return {title: passwords}