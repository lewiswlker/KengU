"""
HKU Authentication Package
验证HKU Portal邮箱和密码
"""

from .auth_hku import verify_hku_credentials

__all__ = ["verify_hku_credentials"]
