import time
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)
        
        logger.info(
            f"{request.method} {request.path} "
            f"status={response.status_code} "
            f"time={duration_ms}ms"
        )
        
        print(
            f"[LOG] {request.method} {request.path} "
            f"| status={response.status_code} "
            f"| time={duration_ms}ms"
        )
        
        return response