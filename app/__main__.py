import argparse
from dataclasses import dataclass

import uvicorn
import uvicorn.config

from app.logging import _level
from app.settings import get_settings



_SETTINGS = get_settings()



@dataclass
class ArgsModel:
    port: int
    reload: bool



def main():
    logging_config = uvicorn.config.LOGGING_CONFIG
    logging_config['formatters']['default']['fmt'] = '%(asctime)s %(levelprefix)s %(message)s'
    logging_config['formatters']['access']['fmt'] = '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    
    logging_config['loggers']['uvicorn']['handlers'] = ['default', 'watchtower']
    logging_config['loggers']['uvicorn']['level'] = _level
    logging_config['loggers']['uvicorn.error']['level'] = _level
    
    logging_config['loggers']['uvicorn.access']['handlers'] = ['access', 'watchtower']
    logging_config['loggers']['uvicorn.access']['level'] = _level

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000)
    parser.add_argument('-r', '--reload', action=argparse.BooleanOptionalAction, default=False)
    
    args = ArgsModel(**vars(parser.parse_args()))

    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=args.port,
        reload=args.reload,
        log_config=logging_config,
        forwarded_allow_ips='172.18.0.0/15',
    )



if __name__ == '__main__': main()