"""
===============================================================================
FILE: cipher_utils.py (STATIC - NO CHANGES NEEDED)
===============================================================================
Text-based encryption/decryption utilities using Caesar cipher
Reusable module for any project needing simple text encryption
"""

CIPHER_SHIFT = 13  # ROT13-style shift

def text_encrypt(text: str) -> str:
    """
    Encrypt text using Caesar cipher
    
    Args:
        text: Plain text to encrypt
        
    Returns:
        Encrypted text
        
    Example:
        >>> text_encrypt("john@email.com")
        'wbua@rznvy.pbz'
    """
    result = []
    for char in text:
        if char.isalpha():
            if char.isupper():
                result.append(chr((ord(char) - 65 + CIPHER_SHIFT) % 26 + 65))
            else:
                result.append(chr((ord(char) - 97 + CIPHER_SHIFT) % 26 + 97))
        elif char.isdigit():
            result.append(str((int(char) + CIPHER_SHIFT) % 10))
        else:
            result.append(char)
    return ''.join(result)

def text_decrypt(text: str) -> str:
    """
    Decrypt text using Caesar cipher
    
    Args:
        text: Encrypted text to decrypt
        
    Returns:
        Decrypted text
        
    Example:
        >>> text_decrypt("wbua@rznvy.pbz")
        'john@email.com'
    """
    result = []
    for char in text:
        if char.isalpha():
            if char.isupper():
                result.append(chr((ord(char) - 65 - CIPHER_SHIFT) % 26 + 65))
            else:
                result.append(chr((ord(char) - 97 - CIPHER_SHIFT) % 26 + 97))
        elif char.isdigit():
            result.append(str((int(char) - CIPHER_SHIFT) % 10))
        else:
            result.append(char)
    return ''.join(result)