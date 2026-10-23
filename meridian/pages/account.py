import reflex as rx
from ..components.book import book
from ..components.brand import brand
from ..components.common import label
from ..state import State


def notice():
    return rx.cond(State.message != '', rx.el.p(State.message, class_name='notice', role='status'), rx.fragment())


def protected(content):
    return rx.cond(State.authenticated, content, rx.el.div(rx.el.p('Opening your secure dossier…'), notice(), rx.el.a('Sign in', href='/login'), class_name='container notice'))


def account_nav():
    return rx.el.header(rx.el.div(brand(), rx.el.nav(
        rx.el.a('Dashboard', href='/dashboard', class_name='nav-link'),
        rx.el.a('Edit profile', href='/profile', class_name='nav-link'),
        rx.el.button('Sign out', on_click=State.logout, class_name='btn-ghost'),
        class_name='row wrap', style={'gap':'20px'}), class_name='container nav-inner'), class_name='nav')


def auth_page(register=False):
    def field(title, name, kind='text'):
        return rx.el.div(rx.el.label(title, html_for='auth-'+name),
            rx.el.input(name=name, id='auth-'+name, type=kind, required=True, class_name='input',
                auto_complete='name' if name=='name' else 'email' if name=='email' else 'new-password' if register else 'current-password',
                **({'min_length':12, 'max_length':128} if name=='password' and register else {})), class_name='field')
    return rx.el.div(rx.el.header(rx.el.div(brand(), class_name='container nav-inner'), class_name='nav'),
        rx.el.main(rx.el.aside(book(), rx.el.h2('Your next chapter, bound in possibility.', class_name='h2'),
            rx.el.p('One personal dossier. Every ambition, carefully kept.', class_name='lede'), class_name='auth-aside'),
            rx.el.div(label('A world ahead', 'blue'), rx.el.h1('Create your dossier' if register else 'Welcome back', class_name='h1'),
                notice(), rx.form(
                    *([field('Full name', 'name')] if register else []), field('Email address', 'email', 'email'),
                    field('Password · 12–128 characters' if register else 'Password', 'password', rx.cond(State.show_password, 'text', 'password')),
                    rx.el.button(rx.cond(State.show_password, 'Hide password', 'Show password'), type='button', on_click=State.toggle_password, class_name='btn-ghost'),
                    rx.el.button(rx.cond(State.auth_busy, 'Opening…', 'Create account' if register else 'Sign in'), type='submit', disabled=State.auth_busy, class_name='tab-button'),
                    on_submit=State.register if register else State.login, reset_on_submit=True, class_name='auth-form'),
                rx.el.div(
                    rx.el.a(
                        'Already registered? Sign in' if register else 'Create Account',
                        href='/login' if register else '/register',
                        class_name='tab-button' if not register else 'nav-link',
                    ),
                    style={'marginTop':'24px'},
                ),
                class_name='page-enter'), class_name='container auth-grid', style={'padding':'40px 28px'}))


def login_page():
    return auth_page()


def register_page():
    return auth_page(True)


def dashboard_page():
    return protected(rx.el.div(account_nav(), rx.el.main(
        rx.el.section(rx.el.div(label('Your personal study atlas', 'blue'), rx.el.h1('Welcome, ', State.student_name, class_name='h1'),
            rx.el.p(State.target_program, class_name='lede'), notice(),
            rx.el.div(rx.el.a('Edit profile', href='/profile', class_name='tab-button'), rx.el.a('Review analysis', href='/analysis', class_name='btn-ghost'), class_name='row wrap', style={'gap':'16px','marginTop':'28px'})), book(), class_name='chapter-grid'),
        rx.el.div(
            rx.el.section(label('Profile'), rx.el.h2(State.completion_str, class_name='num-key'), rx.el.div(rx.el.i(style={'width':State.completion_str}), class_name='progress'), rx.el.p('Based on seven core dossier fields. Other preferences are optional.', class_name='body'), class_name='sheet sheet-pad'),
            rx.el.section(label('Preferred regions'), rx.cond(State.regions.length()>0, rx.foreach(State.regions, lambda r: rx.el.p(r, class_name='h3')), rx.el.p('Choose where your next chapter begins.', class_name='body')), class_name='sheet sheet-pad'),
            rx.el.section(label('Documents'), rx.el.h2(State.docs_count.to_string()+' stored', class_name='h3'), rx.foreach(State.uploaded_slots, lambda slot: rx.el.p(State.docs.get(slot+'_name', '')+' · '+State.docs.get(slot+'_status', ''), class_name='body')), rx.el.p('Text previews are available on the admissions desk; image OCR is not available.', class_name='body'), rx.el.a('Admissions desk →', href='/documents'), class_name='sheet sheet-pad'),
            rx.el.section(label('Living preferences'), rx.el.h3(rx.cond(State.profile['accommodation'] != '', State.profile['accommodation'], 'Choose accommodation'), class_name='h3'), rx.el.p(rx.cond(State.profile['commute'] != '', State.profile['commute'], 'Choose commute preferences'), class_name='body'), rx.cond(State.profile['commute_minutes'] != '', rx.el.p('Maximum commute: ', State.profile['commute_minutes'], ' minutes'), rx.fragment()), rx.el.p('Preferences are saved; the current matcher does not use them.', class_name='body'), class_name='sheet sheet-pad'),
            rx.el.section(label('Profile summary'), rx.el.h3(State.profile['degree'], class_name='h3'), rx.el.p(State.profile['university'], class_name='body'), rx.el.p(State.profile['intake'], class_name='body'), rx.el.p(State.profile['funding'], class_name='body'), class_name='sheet sheet-pad'), class_name='dashboard-grid'),
        rx.el.section(label('Most recent saved analysis'), rx.el.h2(State.prediction_text, class_name='h3'), rx.el.p(State.prediction_confidence, class_name='body'), rx.foreach(State.event_log, lambda message: rx.el.p(message, class_name='notice')), rx.el.p(State.recommendations.length().to_string()+' catalog matches saved.', class_name='body'), rx.foreach(State.recommendations, lambda row: rx.el.p(row['name'], ' · ', row['country'], class_name='h3')), rx.el.a('Open your dossier →', href='/results'), class_name='sheet sheet-pad'),
        class_name='container', style={'padding':'40px 28px 80px'})))
