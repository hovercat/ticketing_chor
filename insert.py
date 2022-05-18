#!/usr/bin/python

from constants import *
from mapper import Mapper

m = Mapper(DB_URL, DB_OPTIONS)

print(DB_URL)
print(DB_OPTIONS)

stmtn = []
with open('db/production_create.sql', encoding='utf-8') as sqlf:
    for line in sqlf:
        #line = line.strip()

        if line.endswith(';\n'):
            stmtn.append(line)

            _stmnt = ''.join(stmtn)
            #print(_stmnt.encode('UTF-8'))
            try:
                m.connection.execute(_stmnt)#.encode('UTF-8'))
            except Exception as e:
                print(e)
                #print('[failed]')
            stmtn = []
        elif line.startswith('\\'):
            stmtn = []
            print(line)
            m.connection.execute(line)
        else:
            stmtn.append(line)

m.session.commit()
m.connection.close()
