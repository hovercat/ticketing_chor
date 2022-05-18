import sys
import logging

#logging.basicConfig(level=logging.DEBUG, filename='/home/k004332/ticketing.log')
sys.path.append('/var/www/html/ticketing_chor_220517/')
#sys.path.append('/home/k004332/miniconda3/envs/event_ticketing/bin/')
#import frontend.app as application
from frontend.app import app as application

if __name__ == '__main__':
    application.run(debug=True)
