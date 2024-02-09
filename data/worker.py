from celery import Celery
from celery.result import AsyncResult

celery_app = Celery(
    'celery_app',
    broker=f"redis://redis:6379/0",
    backend=f"data.backend.CustomBackend://redis:6379/1",
    broker_connection_retry_on_startup=True,
    result_serializer='pickle',

    # export C_FORCE_ROOT="true", pickle is okay here, closed network 
    accept_content=['pickle', 'json'],
)

def request_data(idx: int, ctx_window: int) -> AsyncResult:
    return celery_app.send_task('prepare_data', args=[idx, ctx_window])

