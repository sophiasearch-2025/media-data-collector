class QueueKeyConfig:
    # Colas de RabbitMQ usadas para el logging
    QUEUE_CRAWLER_LOGS = "crawler_log_queue"
    QUEUE_SCHEDULER_LOGS = "scheduler_log_queue"
    QUEUE_SCRAPING_LOGS = "scraping_log_queue"
    QUEUE_CONTROL = "logging_control_queue"

    # Keys de Redis usadas para el logging
    KEY_CRAWLER_ERRORS = "crawler_errors"
    KEY_SCHEDULER_ERRORS = "scheduler_errors"
    KEY_SCRAPING_RESULTS = "scraping_results"
    KEY_CONTROL = "logging_control"
