#!/bin/bash
cd src && zip -r server.zip server.py config.cfg config-secrets.cfg && mv server.zip .. && cd ..