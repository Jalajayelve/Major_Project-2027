"""Disposable browser E2E, including desktop/tablet/mobile screenshots.

Run with .venv Python after installing requirements-test.txt and Chromium.
Starts isolated servers on 3100/8100/8101; uses no real student information.
"""
import os
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import httpx
import psutil
from playwright.sync_api import sync_playwright, expect
sys.stdout.reconfigure(encoding='utf-8')
expect.set_options(timeout=20000)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
env = {**os.environ, 'MERIDIAN_DATA_DIR': str(ROOT/'.test-data'/uuid.uuid4().hex),
       'MERIDIAN_API_URL': 'http://127.0.0.1:8101', 'PLAYWRIGHT_BROWSERS_PATH': str(ROOT/'.test-browsers'),
       'REFLEX_API_URL': 'http://127.0.0.1:8100',
       'PYTHONIOENCODING': 'utf-8'}
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = env['PLAYWRIGHT_BROWSERS_PATH']
processes = []
logs = []
frontend_env_path = ROOT / '.web/env.json'
original_frontend_env = frontend_env_path.read_bytes()


def start(name, command, cwd=ROOT):
    log = (OUT/(name+'.log')).open('w', encoding='utf-8')
    logs.append(log)
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    processes.append(process)


def wait_url(url):
    with httpx.Client(trust_env=False, timeout=3) as client:
        deadline = time.monotonic()+150
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('A test server exited. See test-results/*.log')
            try:
                if client.get(url).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(.5)
    raise RuntimeError('Test server did not become ready: '+url)


def snapshot(page, name):
    page.screenshot(path=str(OUT/(name+'.png')), full_page=True)


def responsive(page, name):
    for width, height in [(1440,1000), (768,1024), (390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        snapshot(page, f'{name}-{width}')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), f'{name} overflows at {width}'
    page.set_viewport_size({'width':1440,'height':1000})


try:
    frontend_env = json.loads(original_frontend_env)
    for key, value in frontend_env.items():
        if isinstance(value, str) and value.startswith(('http://', 'ws://')):
            from urllib.parse import urlsplit, urlunsplit
            parts = urlsplit(value)
            frontend_env[key] = urlunsplit((parts.scheme, '127.0.0.1:8100', parts.path, parts.query, parts.fragment))
    frontend_env_path.write_text(json.dumps(frontend_env), encoding='utf-8')
    start('api', [str(ROOT/'.venv-backend/Scripts/python.exe'), '-m','uvicorn','app:app','--app-dir','backend','--host','127.0.0.1','--port','8101'])
    start('reflex', [sys.executable,'-m','reflex','run','--backend-only','--backend-port','8100','--backend-host','127.0.0.1'])
    start('frontend', ['node', str(ROOT/'.web/node_modules/@react-router/dev/bin.cjs'), 'dev', '--host', '127.0.0.1', '--port', '3100'], cwd=ROOT/'.web')
    wait_url('http://127.0.0.1:8101/health')
    wait_url('http://localhost:3100')
    print('Test servers ready', flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.set_default_timeout(20000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())
        try:
            page.goto('http://localhost:3100/profile')
            expect(page).to_have_url(re.compile('/login$'))
            responsive(page, 'login')
            page.locator('a[href="/register"]').click()
            email = 'browser-'+uuid.uuid4().hex+'@example.com'
            password = 'Test-'+uuid.uuid4().hex
            page.get_by_label('Full name', exact=True).fill('Browser Test Student')
            page.get_by_label('Email address', exact=True).fill(email)
            page.locator('#auth-password').fill(password)
            page.get_by_role('button', name='Show password', exact=True).click()
            expect(page.locator('#auth-password')).to_have_attribute('type', 'text')
            page.get_by_role('button', name='Hide password', exact=True).click()
            page.get_by_role('button', name='Create account', exact=True).click()
            expect(page).to_have_url(re.compile('/dashboard$'))
            expect(page.get_by_role('heading', name='Welcome, Browser Test Student')).to_be_visible()
            print('Registration and protected routes passed', flush=True)
            page.get_by_role('button', name='Sign out', exact=True).click()
            page.goto('http://localhost:3100/login')
            page.get_by_label('Email address').fill(email)
            page.get_by_label('Password', exact=True).fill(password)
            page.get_by_role('button', name='Sign in', exact=True).click()
            expect(page).to_have_url(re.compile('/dashboard$'))
            page.get_by_role('link', name='Edit profile', exact=True).first.click()
            page.get_by_label('Phone', exact=True).fill('abc')
            page.get_by_role('button', name='Save changes', exact=True).click()
            expect(page.get_by_text('Enter a phone number', exact=False)).to_be_visible()
            page.get_by_label('Phone', exact=True).fill('9876543210')
            page.get_by_label('Calling code').select_option('+91')
            page.get_by_role('button', name=re.compile('^02')).click()
            page.get_by_label('GPA / percentage').fill('3.4')
            page.get_by_label('Scale', exact=True).select_option('4')
            page.get_by_role('button', name=re.compile('^03')).click()
            page.locator('#f-gre_verbal').fill('150')
            page.locator('#f-gre_quant').fill('160')
            page.locator('#f-toefl').fill('100')
            page.wait_for_timeout(600)  # Allow controlled-input change events to reach Reflex.
            page.get_by_role('button', name=re.compile('^04')).click()
            page.get_by_label('Years of work experience').fill('1')
            page.locator('#f-research_experience').fill('0')
            for key, value in dict(leadership_score='6', research_score='9', competition_score='5', volunteering_score='4', publication_count='3', patent_count='0').items():
                page.locator('#f-'+key).fill(value)
            page.locator('#f-agent7_degree_level').select_option('Masters')
            page.locator('#f-agent7_field').select_option('STEM')
            page.wait_for_timeout(600)
            page.get_by_role('button', name=re.compile('^05')).click()
            page.get_by_label('Degree', exact=True).select_option('MS')
            page.get_by_label('Field of study', exact=True).fill('Computer Science')
            page.get_by_label('Matching country').select_option('USA')
            page.get_by_label('Catalog tier filter').select_option('medium')
            page.wait_for_timeout(600)
            page.get_by_role('button', name=re.compile('^07')).click()
            page.locator('#f-regions').fill('Canada')
            page.get_by_role('button', name='Add region').click()
            page.locator('#f-regions').fill('Canada')
            page.get_by_role('button', name='Add region').click()
            expect(page.get_by_role('button', name='Remove Canada')).to_have_count(1)
            page.get_by_role('button', name='Clear all regions').click()
            expect(page.get_by_role('button', name='Remove Canada')).to_have_count(0)
            page.locator('#f-regions').fill('Canada')
            page.get_by_role('button', name='Add region').click()
            page.get_by_label('Accommodation preference').select_option('Off campus')
            page.get_by_label('Commute preference', exact=True).select_option('Public transport')
            page.get_by_label('Maximum commute (minutes)').fill('30')
            page.wait_for_timeout(600)
            page.get_by_role('button', name='Save changes', exact=True).click()
            expect(page.get_by_text('All changes saved', exact=True)).to_be_visible()
            responsive(page, 'profile')
            page.goto('http://localhost:3100/dashboard')
            expect(page.get_by_text('Off campus', exact=True)).to_be_visible()
            responsive(page, 'dashboard')
            print('Profile validation, saved regions/preferences and responsive layouts passed', flush=True)
            page.get_by_role('link', name=re.compile('Admissions desk')).click()
            page.locator('input[type=file]').first.set_input_files({'name':'resume.txt','mimeType':'text/plain','buffer':b'Test resume document'})
            expect(page.get_by_text('resume.txt', exact=True)).to_be_visible()
            expect(page.get_by_text('Processed', exact=True)).to_be_visible()
            page.reload()
            expect(page.get_by_text('resume.txt', exact=True)).to_be_visible()
            responsive(page, 'documents')
            page.get_by_role('button', name='Download', exact=True).click()
            page.get_by_role('button', name=re.compile('Start analysis')).click()
            page.get_by_role('button', name='Run / retry analysis', exact=True).click()
            expect(page.get_by_role('button', name='View available results')).to_be_visible()
            page.get_by_role('button', name='View available results').click()
            expect(page.get_by_text(re.compile('Agent 7 extracurricular strength:'))).to_be_visible()
            page.reload()
            expect(page.get_by_text(re.compile('Agent 7 extracurricular strength:'))).to_be_visible()
            expect(page.get_by_role('heading', name='Northeastern University', exact=True)).to_be_visible()
            responsive(page, 'results')
            with page.expect_download() as download:
                page.get_by_role('button', name='Download report', exact=True).click()
            download.value.save_as(str(OUT/'test-dossier.pdf'))
            assert (OUT/'test-dossier.pdf').read_bytes().startswith(b'%PDF')
            page.goto('http://localhost:3100/dashboard')
            page.get_by_role('link', name='Edit profile', exact=True).first.click()
            page.get_by_role('button', name=re.compile('^02')).click()
            page.get_by_label('GPA / percentage').fill('4')
            page.wait_for_timeout(600)
            page.get_by_role('button', name='Cancel', exact=True).click()
            page.get_by_role('link', name='Edit profile', exact=True).first.click()
            page.get_by_role('button', name=re.compile('^02')).click()
            expect(page.get_by_label('GPA / percentage')).to_have_value('3.4')
            page.get_by_label('GPA / percentage').fill('4')
            page.wait_for_timeout(600)
            page.get_by_role('button', name='Save changes', exact=True).click()
            expect(page.get_by_text('All changes saved', exact=True)).to_be_visible()
            page.goto('http://localhost:3100/dashboard')
            page.get_by_role('link', name='Review analysis', exact=True).click()
            page.get_by_role('button', name='Run / retry analysis', exact=True).click()
            page.get_by_role('button', name='View available results').click()
            expect(page.get_by_role('heading', name='Harvard University', exact=True)).to_be_visible()
            page.goto('http://localhost:3100/dashboard')
            page.get_by_role('button', name='Sign out', exact=True).click()
            page.goto('http://localhost:3100/results')
            expect(page).to_have_url(re.compile('/login$'))
            assert not errors, errors
            print('PASS: complete browser journey, documents, real API matching, PDF, edit/cancel/reanalysis/logout; no page errors', flush=True)
        except Exception:
            snapshot(page, 'failure')
            print(page.locator('body').inner_text()[:12000], flush=True)
            raise
        finally:
            browser.close()
finally:
    for process in reversed(processes):
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children:
                child.terminate()
            parent.terminate()
            _, alive = psutil.wait_procs(children+[parent], timeout=5)
            for child in alive:
                child.kill()
        except psutil.NoSuchProcess:
            pass
    for log in logs:
        log.close()
    frontend_env_path.write_bytes(original_frontend_env)
