"""Coarse-grained Python services shared by the Quick modules."""


def tell(signal, *args) -> None:
    """Emit a worker's result. When the window went away while the job ran (closing during a computation)
    the signal's object is gone and there is nobody left to tell; any other error is a real one."""
    try:
        signal.emit(*args)
    except RuntimeError as error:
        if "deleted" not in str(error):
            raise
