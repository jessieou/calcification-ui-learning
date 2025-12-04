import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, "/usr/project/cynthia/web/mammo-ui")
from learning_app import server as application