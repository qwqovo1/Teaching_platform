# login-demo/modules/utils.py
import re
from datetime import datetime
from .database import clean_expired_users

def validate_password_strength(password: str) -> tuple[bool, str]:
    """验证密码强度（至少 6 位）"""
    if len(password) < 6:
        return False, "密码长度不能少于 6 位"
    return True, ""

def validate_username(username: str) -> tuple[bool, str]:
    """验证用户名格式"""
    if not username:
        return False, "用户名不能为空"
    if len(username) < 2:
        return False, "用户名长度不能少于 2 位"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "用户名只能包含字母、数字和下划线"
    return True, ""

def cleanup_if_needed():
    """定期清理过期用户（每天调用一次）"""
    clean_expired_users()