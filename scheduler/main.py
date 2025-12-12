import sys

from scheduler.scheduler import Scheduler

"""
************************
Ejecutar desde la raíz del repositorio como
python -m scheduler.main <medio> <cantidad_de_scrapers>
************************
"""


def main():
    if len(sys.argv) != 3:
        print(
            "Se debe ejecutar con python -m scheduler.main <medio> <cantidad_de_scrapers>"
        )
        sys.exit(1)

    medio = sys.argv[1]
    n_scrapers = int(sys.argv[2])
    scheduler = Scheduler(medio, n_scrapers)
    try:
        scheduler.run()
    except KeyboardInterrupt:
        pass

    sys.exit(0)


if "__main__" == __name__:
    main()
