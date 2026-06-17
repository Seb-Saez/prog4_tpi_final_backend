"""
Rate limiter global de la aplicación.
"""
from fastapi_throttle import RateLimiter

register_limiter = RateLimiter(times=5, seconds=900)  # 5 requests por 15 minutos

login_limiter = RateLimiter(times=5, seconds=900)  # 5 requests por 15 minutos 