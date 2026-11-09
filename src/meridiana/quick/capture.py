"""Quick screenshots with a verified mapping from logical to physical pixels."""


def grab(window):
    """The software renderer returns physical pixels but omits the image's DPR."""
    image = window.grabWindow()
    if image.isNull():
        raise RuntimeError('The Quick window did not render an image')
    ratio = window.effectiveDevicePixelRatio()
    if abs(image.width() - window.width() * ratio) > 1 or abs(image.height() - window.height() * ratio) > 1:
        raise RuntimeError('Screenshot dimensions do not match the Quick window')
    image.setDevicePixelRatio(ratio)
    return image
