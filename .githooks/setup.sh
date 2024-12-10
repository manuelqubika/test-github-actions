#!/bin/bash

# Set permissions for the hook
chmod +x pre-commit

# Set hook path in the main repository
git config core.hooksPath .githooks

# Set hook path for each submodule
git submodule foreach 'git config core.hooksPath ../.githooks'
