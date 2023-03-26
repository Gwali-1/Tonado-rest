import tornado.web
import asyncio


#subhandlers

class BaseHander(tornado.web.RequestHandler):

    async def make_query(self,statement,*args):
        '''takes sql statement to excute and placeholder arguments to be inserted
            execute as await make_query()
        '''
        with(await self.db.cursor()) as cur:
            results = await cur.execute(statement,args)
            if not results:
                return None
            return results
        
    

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
                
                


class LOGINHandler(tornado.web.RequestHandler):
    pass


class CREATEACCOUNTHandler(tornado.web.RequestHandler):
    pass

class GETAPIKEYHandler(tornado.web.RequestHandler):
    pass


class CALLAPIhandler(tornado.web.RequestHandler):
    pass






#application object

def make_app(settings):
    return tornado.web.Application([
        

    ] *settings)



# main func
async def main():
    pass


