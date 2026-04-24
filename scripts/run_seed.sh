#!/bin/bash
cd /home/hoangviet/frappe-bench/sites
PYTHONPATH=/home/hoangviet/frappe-bench/apps/frappe:/home/hoangviet/frappe-bench/apps/erpnext:/home/hoangviet/frappe-bench/apps/assetcore \
  /home/hoangviet/frappe-bench/env/bin/python /home/hoangviet/frappe-bench/apps/assetcore/scripts/seed_runner.py
