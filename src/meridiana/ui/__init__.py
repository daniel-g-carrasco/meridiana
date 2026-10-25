"""The Qt side of Meridiana: it shows the project and triggers the logic, it does not decide.
The plan editor is a QGraphicsView, the 3D view Qt Quick 3D; everything they draw comes from the
plain-Python modules of the package."""


def tell(signal, *args) -> None:
    """Emit a worker's result. When the window went away while the job ran (closing during a computation)
    the signal's object is gone and there is nobody left to tell; any other error is a real one."""
    try:
        signal.emit(*args)
    except RuntimeError as error:
        if "deleted" not in str(error):
            raise
