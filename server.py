import tornado.web
import asyncio
import tornado.ioloop
import sqlite3




def get_db_connection():
    '''create user table in database if not exist and returns connection object '''
    connection = sqlite3.connect("session.sql")
    cursor= connection.cursor()
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS Users(id INTEGER PRIMARY KEY , Name TEXT, Tokens INTEGER DEFAULT 10), Api_Key TEXT ")
        print("DATABASE INITIALIZED")
        return connection
    except Exception as e:
        print(e)
    finally:
        cursor.close()



#subhandlers
class BaseHander(tornado.web.RequestHandler):
    def initialize(self, connection_object=None):
        '''takes db connection object as init argument and assigns it as a member variable'''
        if connection_object is None:
            pass
        self.db = connection_object


    def make_query(self,statement,*args):
        '''takes sql statement to excute and placeholder arguments to be inserted
            executed asynchronously using torn
        '''
        cursor = self.db.cursor()
        results = cursor.execute(statement,args)
        return None if not results else results
        
    

    async def prepare(self):
        '''
            get_current_user cannot be a coroutine
            want to execute query statement asyncronously to get user from db/session info
            hence using the prepare method instead to get user 
        '''
        user_id = self.get_secure_cookie("account_user")
        if not user_id:
            self.redirect("/createAccount")
            try:
                self.current_user = await self.make_query("select * from Users where id = ?", int(user_id))
                if self.current_user is None:
                    self.redirect("/createAccount")
            except Exception as e:
                self.write(e)

                
class HomeHandler(BaseHander):
    pass


class LOGINHandler(BaseHander):
    pass


class CREATEACCOUNTHandler(BaseHander):
    pass

class GETAPIKEYHandler(BaseHander):
    pass


class CALLAPIhandler(BaseHander):
    pass






#application object

def make_app(settings,db):
    return tornado.web.Application([
        ("/",HomeHandler,dict(conn_object=db))
        ("/login",LOGINHandler, dict(conn_object=db)),
        ("/createacct",CREATEACCOUNTHandler, dict(conn_object=db))
        ("/getkey",GETAPIKEYHandler,dict(conn_object=db))
        
    ] *settings)



# main func
async def main():
    app = make_app({})
    app.listen(8886)
    print("server up on port 8886")
    await asyncio.Event().wait()


