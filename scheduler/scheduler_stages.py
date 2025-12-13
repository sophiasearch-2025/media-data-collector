from enum import Enum, auto


class SchedulerStages(Enum):
    # Fases de inicio
    INIT = auto()
    START_LOGGER = auto()
    START_SENDER = auto()
    START_CRAWLER = auto()
    START_SCRAPERS = auto()

    # Ejecución
    RUNNING_MAIN_LOOP = auto()

    # Finalización de las tareas
    # para la detención natural
    CRAWLING_COMPLETE = auto()
    STOPPING_SCRAPERS_GRACEFUL = auto()
    STOPPING_SENDER_GRACEFUL = auto()

    # Finalización de tareas
    # para la detención forzada-controlada
    # (Mid-ejecución: por acción de usuario,
    # o bien, por error del scheduler)
    INTERRUPT_RECEIVED = auto()
    STOPPING_CRAWLER_FORCEFUL = auto()
    STOPPING_SCRAPERS_FORCEFUL = auto()
    STOPPING_SENDER_FORCEFUL = auto()

    CLOSING_LOGGER = auto()
    SHUTDOWN_COMPLETE = auto()
