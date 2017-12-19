#!/bin/bash
cd src && zip -r ion.zip ion.py config.cfg config-secrets.cfg && mv ion.zip .. && cd ..