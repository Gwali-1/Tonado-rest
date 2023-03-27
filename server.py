import tornado.web
import asyncio
import tornado.ioloop
import tornado.concurrent
import tornado.httpclient
import sqlite3
import os
import bcrypt
import uuid


SALT = bcrypt.gensalt()

def get_db_connection():
    '''create user table in database if not exist and returns connection object '''
    connection = sqlite3.connect("session.sql")
    cursor= connection.cursor()
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS Users(id INTEGER PRIMARY KEY, Name TEXT UNIQUE, Password TEXT, Tokens INTEGER DEFAULT 10, ApiKey TEXT)")
        print("DATABASE INITIALIZED")
    except Exception as e:
        print(e)
    finally:
        connection.close()



#subhandlers
class BaseHander(tornado.web.RequestHandler):
    def initialize(self, conn_object=None):
        '''takes db connection object as init argument and assigns it as a member variable'''
        if conn_object is None:
            pass
        self.db = conn_object


    def execute_query(self,statement,*args):
        '''takes sql statement to excute and placeholder arguments to be inserted
            executed asynchronously using torn
        '''
        connection = sqlite3.connect("session.sql")
        cursor = connection.cursor()
        try:
            results = cursor.execute(statement,args)
            connection.commit()
            return None if not results else results.fetchall()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
 

    def generate_hash(self,input):
        try:
            return bcrypt.hashpw(input.encode("utf-8"), SALT )
        except Exception as e:
            print(e)
            return False
        
    def check_password_validity(self,raw_input,hash_input):
        return  bcrypt.checkpw(raw_input.encode("utf-8"),hash_input)


    def generate_api_key(self):
        return str(uuid.uuid4())

    async def get_kanye_quote(self):
        client = tornado.httpclient.AsyncHTTPClient()
        try:
            respone = await client.fetch("https://api.kanye.rest")
            return tornado.escape.json_decode(respone.body)
        except Exception as e:
            raise e

    async def prepare(self):
        '''
            get_current_user cannot be a coroutine
            want to execute query statement asyncronously to get user from db/session info
            hence using the prepare method instead to get user 
        '''

        if self.request.headers.get("Content-Type", "").startswith("application/json"):  #from tornado documentation
            self.json_args = tornado.escape.json_decode(self.request.body)
        else:
            self.json_args = None


        user_id = self.get_secure_cookie("account_user")
        if user_id:
            try:
                query = "select * from Users where id = ?"
                result = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,int(user_id))
                if result is None:
                    self.redirect("/login")
                self.current_user = result[0]
            except Exception as e:
                self.write(e)





                
class HomeHandler(BaseHander):
    async def get(self):
        self.render("home.html")


        


class LOGINHandler(BaseHander):

    def get(self):
        self.render("login.html", message="")

    async def post(self):
        name=self.get_argument("username")
        password = self.get_argument("password")
        query = "SELECT id, Name, Password FROM Users Where name = ?"
        user = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,name) #returns a tuple in a list as result -->[(result)]
        if user:
            if self.check_password_validity(password,user[0][2]):
                self.set_secure_cookie("account_user",str(user[0][0]))
                self.redirect("/")
        self.render("login.html", message="Invalid  credientials")
        







class CREATEACCOUNTHandler(BaseHander):

    def get(self):
        self.render("create.html",message="")

    async def post(self):
        name=self.get_argument("username")
        password = self.get_argument("password")
        password_hash = await tornado.ioloop.IOLoop.current().run_in_executor(None, self.generate_hash,password)
        if not password_hash:
            return self.write("error with hash")
        query= "INSERT INTO Users(Name,Password) VALUES(?,?)"
        try:
            await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,name,password_hash)
            self.redirect("/login")
        except sqlite3.IntegrityError:
            self.render("create.html",message="username taken")

       

class GETAPIKEYHandler(BaseHander):
    @tornado.web.authenticated
    async def post(self):
        user = self.current_user
        key = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.generate_api_key)
        try:
            query = "UPDATE Users SET ApiKey = ? WHERE id = ?"
            await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,key,user[0])
            return tornado.escape.json_encode({"key":key})
        except Exception as e:
            print(e)
     
        


class CALLAPIhandler(BaseHander):
    async def post(self):
        api_key = self.json_args["key"]
        user = self.current_user
        query = "SELECT name from Users WHERE ApiKey = ?"
        result = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,api_key)
        if result[0][0] != api_key:
            pass
        try:
            response = await self.get_kanye_quote()
            return tornado.escape.json_encode(response)
        except:
            return tornado.escape.json_encode({"error":"try again later"})

              





#application object
def make_app(settings,db=None):
    return tornado.web.Application([
        ("/",HomeHandler,dict(conn_object=db)),
        ("/login",LOGINHandler, dict(conn_object=db)),
        ("/createacct",CREATEACCOUNTHandler, dict(conn_object=db)),
        ("/getkey",GETAPIKEYHandler,dict(conn_object=db)),
        
    ] ,**settings)





# main func
async def main():
    app = make_app({
        "cookie_secret":"my-super-secret",
        "debug":"true",
        "template_path": os.path.join(os.path.dirname(__file__),"templates"),
        "static_path":os.path.join(os.path.dirname(__file__),"static"),
        "login_url": "/login",
        "xsrf_cookies": True,
        "compiled_template_cache":False

    })

    app.listen(8886)
    print("server up on port 8886 ...")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())



