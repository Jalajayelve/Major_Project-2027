import reflex as rx
from .brand import monogram


def book():
    return rx.el.div(
        rx.el.div(rx.el.div(class_name='book-pages'),
            rx.el.div(rx.el.span('MERIDIAN · YOUR NEXT CHAPTER'), class_name='book-spine'),
            rx.el.div(monogram(72), rx.el.span('MERIDIAN', class_name='book-title'),
                rx.el.hr(), rx.el.p('A world of possibility.\nA dossier of your own.'),
                rx.el.span('STUDY ABROAD · PERSONAL DOSSIER', class_name='mono'), class_name='book-cover'),
            class_name='book-object'), class_name='book-stage', aria_hidden='true')
