#!/bin/python
import argparse
import json
import pathlib
import re
from typing import Final

import requests
from bs4 import BeautifulSoup
from selenium import webdriver


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Enter domain name (-d) to pull acquisition from SecurityTrails.com or company name (-c) to query Crunchbase.')
    parser.add_argument("--domain", help="Domain name to pull acquisition data for")
    parser.add_argument("--email", help="Email address for SecurityTrails login")
    parser.add_argument("--password", help="Password for SecurityTrails login")
    parser.add_argument("--company-name", help="Company name to query Crunchbase")
    parser.add_argument("--output", required=True, help="Output JSON file to save results")

    return parser.parse_args()


def get_security_trails_acquisitions(domain, email, password):
    session = requests.Session()

    # Get CSRF token
    response = session.get('https://securitytrails.com/app/account')
    soup = BeautifulSoup(response.content, 'html.parser')
    all_scripts = soup.find_all('script')
    csrf_script = all_scripts[9]

    for line in csrf_script:
        csrf_token = line.split('"')[3]

    # Login
    login_payload = {
        "_csrf_token": csrf_token,
        "login": {
            "email": email,
            "password": password
        }
    }
    login_url = 'https://securitytrails.com/app/api/console/account/login'
    session.post(login_url, json=login_payload)

    # Get acquisition data
    acquisition_url = f'https://securitytrails.com/app/api/v1/surface_browser/acquisitions/{domain}'
    acquisition_response = session.get(acquisition_url)

    if acquisition_response.status_code == 200:
        return acquisition_response.json()
    else:
        return {
            "error": f"Failed to retrieve data for domain {domain}. Status code: {acquisition_response.status_code}"}


def get_crunch_base_acquisitions(company):
    driver = webdriver.Chrome()
    url = f"https://www.crunchbase.com/organization/{company}/company_financials"
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pattern = "acquired by"
    acquisitions = []
    for string in soup.strings:
        if re.search(pattern, string):
            cleaned_string = string.strip()
            if not re.search(r'Auto-generated', cleaned_string):
                acquisitions.append({"message": cleaned_string})

    driver.close()
    driver.quit()

    return acquisitions


def main():
    args = parse_arguments()

    results = {}

    MAIN_DIR: Final[pathlib.Path] = pathlib.Path(__file__).parent
    OUTPUT: Final[pathlib.Path] = MAIN_DIR / args.output

    if args.domain and args.email and args.password:
        securitytrails_data = get_security_trails_acquisitions(args.domain, args.email, args.password)
        results['securitytrails'] = securitytrails_data

    if args.company_name:
        crunchbase_data = get_crunch_base_acquisitions(args.company_name)
        results['crunchbase'] = crunchbase_data

    with open(OUTPUT, 'w') as jf:
        json.dump(results, jf, indent=2)


if __name__ == "__main__":
    main()
