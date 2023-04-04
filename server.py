import tornado.web
import tornado.gen
import asyncio
import tornado.ioloop
import tornado.concurrent
import tornado.httpclient
import sqlite3
import os
import bcrypt
import uuid
import time


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
                pass




                
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
        user = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,name) #returns  a list as result -->[(result)]
        if user:
            if self.check_password_validity(password,user[0][2]):
                self.set_secure_cookie("account_user",str(user[0][0]))
                return self.redirect("/")
            
        self.render("login.html", message="Invalid  credientials")
        

# class TestHandler(tornado.web.RequestHandler):
#      def get(self):
#         print("hello")
#         time.sleep(6)
#         print(f"done with{self.request} ")
        



class CREATEACCOUNTHandler(BaseHander):

    def get(self):
        self.render("create.html",message="")

    async def post(self):
        name=self.get_argument("username")
        password = self.get_argument("password")
        password_hash = await tornado.ioloop.IOLoop.current().run_in_executor(None, self.generate_hash,password)
        key = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.generate_api_key)
        if not password_hash:
            return self.write("error with hash") #could be error page or redirect
        query= "INSERT INTO Users(Name,Password,ApiKey) VALUES(?,?,?)"
        try:
            await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,name,password_hash,key)
            self.redirect("/login")
        except sqlite3.IntegrityError:
            self.render("create.html",message="username taken")

       



class GETAPIKEYHandler(BaseHander): #not used in app
    async def post(self):
        user = self.json_args["name"]

        query_statement = "SELECT * FROM Users WHERE Name = ?"
        account = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query_statement,user)
        if not account:
            self.set_status(400)
            return self.write({"error":"could not generate key"})
        
        key = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.generate_api_key)
        try:
            query = "UPDATE Users SET ApiKey = ? WHERE name = ?"
            s= await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,key,user)
            print(s)
            self.set_status(200)
            return self.write({"key":key})
        except Exception as e:
            print(e)
            self.set_status(400)
            return self.write({"error":"could not generate key"})
     
        




class CALLAPIhandler(BaseHander):
    async def post(self):
        api_key = self.json_args["key"]
 
        query = "SELECT name from Users WHERE ApiKey = ?"
        result = await tornado.ioloop.IOLoop.current().run_in_executor(None,self.execute_query,query,api_key)
        if  not result:
            self.set_status(400)
            return self.write({"error":"invalid api key"})
        try:
            response = await self.get_kanye_quote()
            return self.write({"quote":response})
        except:
            self.set_status(400)
            return self.write({"error":"couldnt get quote"})
              



#application object
def make_app(settings,db=None):
    return tornado.web.Application([
        ("/",HomeHandler,dict(conn_object=db)),
        ("/login",LOGINHandler, dict(conn_object=db)),
        ("/createacct",CREATEACCOUNTHandler, dict(conn_object=db)),
        ("/getkey",GETAPIKEYHandler,dict(conn_object=db)),
        ("/getquote",CALLAPIhandler)
        
        
    ] ,**settings)





# main func
async def main():
    app = make_app({
        "cookie_secret":"my-super-secret",
        "debug":"true",
        "template_path": os.path.join(os.path.dirname(__file__),"templates"),
        "static_path":os.path.join(os.path.dirname(__file__),"static"),
        "login_url": "/login",
        "compiled_template_cache":False

    })

    app.listen(8886)
    print("server up on port 8886 ...")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
 


