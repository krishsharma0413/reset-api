# region [imports]
from tetris.impl import custom
from tetris.impl import scorer
import anyio
import json as jsonlib
import random
from core.base_models import *
from core.game_functions import *
from core.image_gen import *
import uuid
import aiohttp
import fastapi
import motor.motor_asyncio
import tetris
import secrets
import xmltodict
from aioify import aioify
from bson.objectid import ObjectId
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo.errors import DuplicateKeyError, CollectionInvalid
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from extras import (art_of_war, edn, emojify_string,
                    morse_decode, morse_encode, text_to_owo, user_info, premium_user_checker)

# mysql connection
mongo = motor.motor_asyncio.AsyncIOMotorClient("mongodb connector")

token = "discord bot token"

limiter = Limiter(key_func=get_remote_address)
app = fastapi.FastAPI(redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# endregion

# region [html templates]

@app.get("/",response_class=HTMLResponse,include_in_schema=False)
@limiter.limit("100/minute")
async def homepage(request:fastapi.Request):
    resp = edn(app)
    return templates.TemplateResponse("index.html",{"request":request,"endpoints":resp})

@app.get("/support",response_class=HTMLResponse,include_in_schema=False)
@limiter.limit("100/minute")
def homepage(request:fastapi.Request):
    return RedirectResponse("https://www.buymeacoffee.com/resetxd")

# endregion

# region [internal endpoints]

def get_redoc_html(
    *,
    openapi_url: str,
    title: str,
    redoc_js_url: str = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    redoc_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
    with_google_fonts: bool = True,
) -> HTMLResponse:
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>{title}</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """
    if with_google_fonts:
        html += """
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    """
    html += f"""
    <link rel="shortcut icon" href="{redoc_favicon_url}">
    <!--
    ReDoc doesn't change outer page styles
    -->
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
    </style>
    </head>
    <body>
    <redoc spec-url="{openapi_url}"></redoc>
    <script src="{redoc_js_url}"> </script>
    <script data-name="BMC-Widget" data-cfasync="false" src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js" data-id="resetxd" data-description="Support me on Buy me a coffee!" data-message="" data-color="#FFDD00" data-position="Right" data-x_margin="18" data-y_margin="18"></script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title= "resapi docs",
        redoc_favicon_url = "/static/avatar1.png"
    )


@app.get("/internal/endpoints",include_in_schema=False)
@limiter.limit("5/minute")
async def end(request: fastapi.Request):
    async with aiohttp.ClientSession() as client:
        response = await client.get(f"{request.url._url[:22]}openapi.json")
        json = await response.json()
        json = json["paths"]
    ret = ""
    for x in json:
        try:
            resp = json[x]["get"]["description"].split("<br>")
            ret += f"""
            <div class="col-md-6" style="margin-bottom: 8px;">
                <div class="card" style="background: rgba(255,255,255,0);border-radius: 22px;margin-top: 0px;border: 3px solid #8a00ff;box-shadow: 5px 5px 20px #8a00ff, -5px -5px 20px #8a00ff;">
                    <div class="card-body">
                        <h4 class="card-title" style="color: #8a00ff;">{x[1:]}</h4>
                        <p class="card-text" style="font-size: 23px;color: #bf00ff;">{resp[0]}</p><a class="card-link" href="{resp[1]}" style="color: #df00ff;">test endpoint</a>
                    </div>
                </div>
            </div>

            """
        except:
            pass
    return ret

@app.get("/asset/{file_path}",include_in_schema=False)
async def asset(requests:fastapi.Request, file_path:str):
    return FileResponse(f"./asset/{file_path}")

# endregion

# region [authentication]

@app.get("/auth",include_in_schema=False)
async def discord_auth(request:fastapi.Request, code:str):
    client_secret = "bot secret"
    redirect_url = "https://api.resetxd.xyz/auth"
    client_id = "849197452082937866"
    api_url = "https://discord.com/api/v10"
    async with aiohttp.ClientSession() as client:
        response = await client.post(api_url+"/oauth2/token", data={"client_id": client_id, "client_secret": client_secret, "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_url})
        json = await response.json()
    thistoken = json["access_token"]
    async with aiohttp.ClientSession() as client:
        response = await client.get(api_url+"/users/@me", headers= {"Authorization": f"Bearer {thistoken}"})
        json = await response.json()
    
    a = await mongo.users.users.find_one({"_id": json["id"]})
    if a is None:
        apitoken = secrets.token_urlsafe(32)
        await mongo.users.users.insert_one({"_id": json["id"], "token": apitoken})
    else:
        apitoken = a["token"]
    return templates.TemplateResponse("authentication.html",{"request":request,"token":apitoken})

# endregion

# region [json endpoints]

@app.get("/art-of-war",tags=["json endpoints"],summary="art of war")
@limiter.limit("100/minute")
def artOfWar(request: fastapi.Request):
    """
    sun tzu the art of war book related quotes<br>/art-of-war<br>

    """
    return {"quote":random.choice(art_of_war)}


@app.get("/art-of-war.json",include_in_schema=False)
@limiter.limit("100/minute")
def artOfWarJson(request: fastapi.Request):
    return {"quote":art_of_war}

@app.get("/emojify",tags=["json endpoints"],summary="emojify")
@limiter.limit("100/minute")
def emojify(request: fastapi.Request,text:str):
    """
    emojify a string<br>/emojify?text=omg+reset+is+the+best<br>

    creates a discord friendly string

    # parameters
    - **text**: text to emojify

    # return
    ```json
    {
        "emojified": "text"
    }
    ```
    """
    return {"emojified":emojify_string(text)}

@app.get("/news",tags=["json endpoints"],summary="myanimelist news")
@limiter.limit("100/minute")
async def news(request: fastapi.Request): 
    """
    gives anime news in json format<br>/news<br>

    # return
    ```json
        [
            {"guid":"", "title":"", "description":"", "media:thumbnail":"", "pubDate":"", "link":""},
            {...},
            {...}
        ]
    ```
    """  
    async with aiohttp.ClientSession() as session:
        async with session.get("https://myanimelist.net/rss/news.xml") as repo:
            resultJson =  await repo.text()
            returnJson = jsonlib.dumps(xmltodict.parse(resultJson))
    return jsonlib.loads(returnJson)["rss"]["channel"]["item"]


@app.get("/user",tags=["json endpoints"],summary="user info")
@limiter.limit("100/minute")
async def user(request: fastapi.Request, userid:str):
    """
    user info<br>/user?userid=424133185123647488<br>

    # parameters
    - **userid**: discord user ID (not user name)

    # return
    ```json
    {
        "name":"reset",
        "avatar":"https://cdn.discordapp.com/avatars/424133185123647488/26fc2ba791f1fcd2f678d5761e2cdab2.png?size=1024",
        "banner":null,
        "discriminator":"8278",
        "id":"424133185123647488",
        "banner_color":"#18191c",
        "accent-color":1579292
    }
    ```
    """
    ret = await user_info(token, userid)
    return ret


@app.get("/strings", tags=["json endpoints"],summary="encoding info")
@limiter.limit("100/minute")
async def strings(request: fastapi.Request, text:str, from_:str=None, to:str=None):
    """
    strings info<br>/strings?text=reset+api+is+the+best&from_=text&to=owo<br>

    # parameters
    - **text**: text to encode
    - **from_**: can be **text** or **morse**
    - **to**: can be **text** or **owo** or **morse**

    # return
    ```json
    {
        "text": "weset api is teh best"
    }
    ```
    """
    if from_ == "text" and to == "owo":
        return {"text":text_to_owo(text)}
    elif from_ == "text" and to == "morse":
        return {"text":morse_encode(text)}
    elif from_ == "morse" and to == "text":
        return {"text":morse_decode(text)}
    else:
        return {"text":text}

# endregion

# region [database endpoints]

@app.get("/database/dashboard",include_in_schema=False)
async def dashboard(request: fastapi.Request, token:str=None):
    if token == None:
        return templates.TemplateResponse("dashboard.html",{"request":request, "entries":"<h1 style='color:white;'>you dont have a token</h1>"})
    else:
        search = await mongo.users.users.find_one({"token": token})
        if search == None:
            return {"success": "invalid token"}
        database = mongo[search["_id"]]
        collections = await database.list_collection_names()
        rett = {}
        for x in collections:
            f = database[x].find({})
            r = await f.to_list(length=10000)
            rett[x] = r
        
        body = """
        <div class="panel-body">
            <div style="margin-left:10px;background-color: black;color:white;">
                {0}
            </div>
        </div>
        <hr style="background-color: aliceblue;">

        """
        default = """
        <div class="panel-group" id="accordion">
            <div class="panel panel-default">
                <div class="panel-heading">
                <h4 class="panel-title"><a class="accordion-toggle" data-toggle="collapse" data-parent="#accordion" href="#collapse{2}">{0}</a></h4></div>
                <div id="collapse{2}" class="panel-collapse collapse in">
                    {1}
                </div>
            </div>
        </div>
        """
        ret="""
        """
        mm = 1
        for x in rett:
            ret += default.format(x,"\n".join([ body.format(str(y)) for y in rett[x]]),mm)
            mm+=1
        pass
    return templates.TemplateResponse("dashboard.html",{"request":request,"entries":ret})


@app.post("/database/create", include_in_schema=True,tags=["database endpoints"],summary="create database")
async def createDB(request: fastapi.Request, create:create_db):
    """
    [POST] method

    create new collection in database

    endpoint - /database/create

    # parameters
    - **token**: user token
    - **name**: name of collection

    # return
    ```json
    {
        "success": "collection created"
    }
    ```
    """
    try:
        search = await mongo.users.users.find_one({"token": create.token})
        if search == None:
            return {"success": "invalid token"}
        database = mongo[search["_id"]]
        await database.create_collection(create.name)
    except Exception as e:
        if type(e) ==  CollectionInvalid:
            return {"success": "collection with that name already exists"}
        else:
            return {"success": "some unknown error"}
    
    return {"success": "collection created"}
    

@app.post("/database/delete",tags=["database endpoints"],summary="delete database")        
async def deleteDB(request: fastapi.Request, delete:create_db):
    """
    [POST] method

    delete an existing collection from the database

    endpoint - /database/delete

    # parameters
    - **token**: user token
    - **name**: name of collection

    # return
    ```json
    {
        "success": "collection deleted"
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": delete.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "database failed to respond"}
    
    database = mongo[search["_id"]]
    await database.drop_collection(delete.name)
    return {"success": "collection deleted"}

@app.post("/database/delete-entry",tags=["database endpoints"],summary="delete entry")        
async def deleteentry(request: fastapi.Request, delete:delete_entry):
    """
    [POST] method

    delete an existing collection from the database

    endpoint - /database/delete-entry

    # parameters
    - **token**: user token
    - **collection**: name of collection where the data is stored
    - **value**: value of entry usually only the _id

    # return
    ```json
    {
        "success": "data deleted"
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": delete.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "database failed to respond"}
    
    database = mongo[search["_id"]]
    await database[delete.collection].delete_one(delete.value)
    return {"success": "data deleted"}

@app.post("/database/delete-entry-many",tags=["database endpoints"],summary="delete entry")        
async def deleteentrymany(request: fastapi.Request, delete:delete_entry):
    """
    [POST] method

    delete an existing collection from the database

    endpoint - /database/delete-entry-many

    # parameters
    - **token**: user token
    - **collection**: name of collection where the data is stored
    - **value**: value of entry usually only the _id

    # return
    ```json
    {
        "success": "data deleted"
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": delete.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "database failed to respond"}
    
    database = mongo[search["_id"]]
    await database[delete.collection].delete_many(delete.value)
    return {"success": "data deleted"}

@app.post("/database/insert-into", tags=["database endpoints"],summary="insert-into database")
async def insertDB(request: fastapi.Request, insert:insert_db):
    """
    [POST] method

    insert data into an existing collection

    endpoint - /database/insert-into

    # parameters
    - **token**: user token
    - **collection**: name of collection to add into
    - **value**: data to add (JSON,Integer, String, etc)

    # return
    ```json
    {
        value you entered + "_id"
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": insert.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "database failed to respond"}
    
    database = mongo[search["_id"]]
    try:
        await database["{}".format(insert.collection)].insert_one(insert.value)
    except Exception as e:
        if type(e) ==  DuplicateKeyError:
            return {"success": "duplicate key"}
        else:
            return {"success": "some unknown error"}
    if insert.value.get("_id") != None and type(insert.value.get("_id")) == ObjectId:
        insert.value["_id"] = str(insert.value["_id"])
    return insert.value

@app.post("/database/find-many", tags=["database endpoints"],summary="find-many database")        
async def findDB(request: fastapi.Request, finder:insert_db):
    """
    [POST] method

    find many entries with similar data from an existing collection

    endpoint - /database/find-many

    # parameters
    - **token**: user token
    - **collection**: name of collection 
    - **value**: data to search (JSON) {mongodb queries like $gt, $lt, $in, etc are also supported}

    # return
    ```json
    {
        "data":[{...}, {...}]
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": finder.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "some unknown error"}
    
    database = mongo[search["_id"]]
    ret = database[finder.collection].find(finder.value)
    ret = await ret.to_list(length=100)
    for x in range(len(ret)):
        if ret[x]["_id"] != None and type(ret[x]["_id"]) == ObjectId:
            ret[x]["_id"] = str(ret[x]["_id"])
    return {"data":ret }


@app.post("/database/leaderboard",tags=["database endpoints"],summary="leaderboard database")        
async def leaderboardDB(request: fastapi.Request, finder:leaderboard_db):
    """
    [POST] method

    manage a certain kind of data from the collection and return it like a leaderboard

    endpoint - /database/leaderboard

    # parameters
    - **token**: user token
    - **collection**: name of collection
    - **key**: key to sort the data by   
    - **order**: asc/desc   

    # return
    ```json
    {
        "data":[{...}, {...}]
    }
    ```
    """
    try:
        search = await mongo.users.users.find_one({"token": finder.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "some unknown error"}
    
    database = mongo[search["_id"]]
    ret = database[finder.collection].find({})
    ret = await ret.to_list(length=1000)
    for x in range(len(ret)):
        if ret[x]["_id"] != None and type(ret[x]["_id"]) == ObjectId:
            ret[x]["_id"] = str(ret[x]["_id"])
    if finder.order == "asc":
        ret.sort(key=lambda x: float(x[finder.key]), reverse=True)
    else:
        ret.sort(key=lambda x: float(x[finder.key]), reverse=False)

    return {"data":ret }

@app.post("/database/find-one", tags=["database endpoints"],summary="find database")        
async def findDB(request: fastapi.Request, finder:insert_db):
    """
    [POST] method

    find single entries from an existing collection

    endpoint - /database/find-one

    # parameters
    - **token**: user token
    - **collection**: name of collection 
    - **value**: data to search (JSON) {mongodb queries like $gt, $lt, $in, etc are also supported}

    # return
    ```json
    {
        "data":{...}
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": finder.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "some unknown error"}
    
    database = mongo[search["_id"]]
    ret = await database[finder.collection].find_one(finder.value)
    if ret == None:
        return {"data":"no data was found"}
    if ret["_id"] != None and type(ret["_id"]) == ObjectId:
        ret["_id"] = str(ret["_id"])
    return {"data":ret }

@app.post("/database/update-one", include_in_schema=False,description="update something in database<br>/database/update",tags=["database endpoints"],summary="update database")        
async def updateDB(request: fastapi.Request, updater:update_db):
    """
    [POST] method

    update single entries from an existing collection

    endpoint - /database/update-one

    # parameters
    - **token**: user token
    - **collection**: name of collection 
    - **where**: data to update/select (JSON) {mongodb queries like $gt, $lt, $in, etc are also supported}
    - **value**: data to update into (JSON) {mongodb queries like $inc, $set, etc are also supported}

    # return
    ```json
    {
        "matched_count":int,
        "modified_count":int,
        "upserted_id":str,
        "raw_result":{...}
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": updater.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "some unknown error"}
    
    database = mongo[search["_id"]]
    ret = await database[updater.collection].update_one(updater.where,updater.value)
    return {"matched_count":ret.matched_count, "modified_count":ret.modified_count, "upserted_id":ret.upserted_id,"raw_result":ret.raw_result}


@app.post("/database/update-many", include_in_schema=False,description="update something in database<br>/database/update-many",tags=["database endpoints"],summary="update-many database")        
async def updateDB(request: fastapi.Request, updater:update_db):
    """
    [POST] method

    update many/all entries from an existing collection

    endpoint - /database/update-many

    # parameters
    - **token**: user token
    - **collection**: name of collection 
    - **where**: data to update/select (JSON) {mongodb queries like $gt, $lt, $in, etc are also supported}
    - **value**: data to update into (JSON) {mongodb queries like $inc, $set, etc are also supported}

    # return
    ```json
    {
        "matched_count":int,
        "modified_count":int,
        "upserted_id":str,
        "raw_result":{...}
    }
    ```
    """

    try:
        search = await mongo.users.users.find_one({"token": updater.token})
        if search == None:
            return {"success": "invalid token"}
    except:
        return {"success": "some unknown error"}
    
    database = mongo[search["_id"]]
    ret = await database[updater.collection].update_many(updater.where,updater.value)
    return {"matched_count":ret.matched_count, "modified_count":ret.modified_count, "upserted_id":ret.upserted_id,"raw_result":ret.raw_result}

# endregion

# region [games endpoint]

# region [game endpoint][connect4]

current_playing = {}

@app.post("/game/connect-4/create",tags=["games endpoints"],summary="create c4 game")
async def create_game(request: fastapi.Request, game:c4_creator):
    """
    [POST] method

    create a new connect 4 game

    endpoint - /game/connect-4/create

    # returns
    ```json
    {
        "game_id": game-token
    }
    ```
    """
    game_id = uuid.uuid4()
    global current_playing
    current_playing[str(game_id)] = {
        "board":create_board(),
        "player1":game.player1,
        "player2":game.player2,
        "empty":game.empty
        }
    return {"game_id":str(game_id)}

@app.get("/game/connect-4/get-all-games",include_in_schema=False)
async def allGames():
    return {"data":current_playing}

@app.post("/game/connect-4/get-board",tags=["games endpoints"],summary="get c4 board")
async def get_board(request: fastapi.Request, game_id:c4_get_board):
    """
    [POST] method

    returns the current game board

    endpoint - /game/connect-4/get-board

    # parameters
    - **game_id** - game token


    # returns
    ```json
    {
        "board": "ready to use board"
    }
    ```
    """

    try:
        global current_board
        return {"board":current_board(current_playing[game_id.game_id]["board"],current_playing[game_id.game_id]["player1"],current_playing[game_id.game_id]["player2"],current_playing[game_id.game_id]["empty"])}
    except:
        return {"eror":"game not found"}

@app.post("/game/connect-4/drop",tags=["games endpoints"],summary="c4 game drop")
async def droper(request: fastapi.Request, drop:c4_drop):
    """
    [POST] method

    drop a piece at a given column

    endpoint - /game/connect-4/drop

    # parameters
    - **game_id** - game token
    - **column** - column to drop piece at
    - **player** - player to drop piece as (1 or 2 only)

    # returns
    ```json
    {
        "winner":"if game is over",
        "board":"updated board"
    }
    ```
    """

    global current_playing
    board = current_playing[drop.game_id]["board"]
    col = int(drop.column)
    if is_valid_location(board,col):
        row = get_next_open_row(board,col)
        drop_piece(current_playing[drop.game_id]["board"],row,col,int(drop.player))
    if winning_move(board, int(drop.player)):
        return {"winner":drop.player,"board":current_board(current_playing[drop.game_id]["board"],current_playing[drop.game_id]["player1"],current_playing[drop.game_id]["player2"],current_playing[drop.game_id]["empty"])}
    else:
        return {"winner":"none","board":current_board(current_playing[drop.game_id]["board"],current_playing[drop.game_id]["player1"],current_playing[drop.game_id]["player2"],current_playing[drop.game_id]["empty"])}


# endregion

# region [game endpoints][tetris]


tetris_current_playing = {}

@app.post("/game/tetris/create",tags=["games endpoints"],summary="create tetris game")
async def tetris_create_game(request: fastapi.Request):
    """
    [POST] method

    create a new tetris game

    endpoint - /game/tetris/create

    # returns
    ```json
    {
        "game_id": game-token,
        board: "ready to use board",
        "next": "next piece"
    }
    ```
    """
    game_id = str(uuid.uuid4())
    global tetris_current_playing
    game = tetris.BaseGame(custom.CustomEngine,board_size=(15,10), scorer=scorer.GuidelineScorer)
    game.engine.parts["gravity"] = PerMoveGravity
    game.reset()
    tetris_current_playing[str(game_id)] = {"game":game}
    return {"game_id":str(game_id), "board":tetris_render_board(game), "next": tetris_next_piece(game)}

@app.post("/game/tetris/action",tags=["games endpoints"],summary="tetris game actions")
async def tetris_action(request: fastapi.Request, action:tetris_action):
    """
    [POST] method

    perform an action on a tetris game

    endpoint - /game/tetris/action

    # parameters
    - **game_id** - game token
    - **action** - action to perform (left, right, rotate, soft_drop, hard_drop, swap, hold)

    # returns
    ```json
    {
        "win": true or false if the game still playing,
        "board":"updated board",
        "next":"next piece"
    }
    ```
    """
    global tetris_current_playing
    if action.action == "left":
        tetris_current_playing[action.game_id]["game"].left()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing) ,"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}
    elif action.action == "right":
        tetris_current_playing[action.game_id]["game"].right()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing),"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}
    elif action.action == "rotate":
        tetris_current_playing[action.game_id]["game"].rotate()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing),"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}
    elif action.action == "soft_drop":
        tetris_current_playing[action.game_id]["game"].soft_drop()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing),"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}
    elif action.action == "hard_drop":
        tetris_current_playing[action.game_id]["game"].hard_drop()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing),"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}
    elif action.action == "swap":
        tetris_current_playing[action.game_id]["game"].swap()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing),"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}
    elif action.action == "hold":
        tetris_current_playing[action.game_id]["game"].swap()
        tetris_current_playing[action.game_id]["game"].tick()
        return {"win":str(tetris_current_playing[action.game_id]["game"].playing),"board":tetris_render_board(tetris_current_playing[action.game_id]["game"]),"score":tetris_current_playing[action.game_id]["game"].score, "next": tetris_next_piece(tetris_current_playing[action.game_id]["game"])}

# endregion

#region [game endpoints][sokoban]

sokoban_currently_playing = {}

@app.post("/game/sokoban/create",tags=["games endpoints"],summary="create sokoban game")
async def push_the_box_create_game(request: fastapi.Request, le:sokobancreate):
    """
    [POST] method

    create a new sokoban game

    endpoint - /game/sokoban/create

    # parameter

    - **level** - level of the game (1,2,3,4,5,etc or name of the custom level)

    # returns
    ```json
    {
        "game_id": game-token,
        board: "ready to use board",
    }
    ```
    """
    game_id = str(uuid.uuid4())
    global sokoban_currently_playing
    levels = await all(mongo)
    game = await create(le.level, levels)
    await update_playcount(mongo ,le.level)
    game["map"] = raw_creator(game["map"])
    game = analyse(game)
    sokoban_currently_playing[str(game_id)] = {"game":game}
    return {"game_id":str(game_id), "board":render_perm(game)}

@app.get("/game/sokoban/all",tags=["games endpoints"],summary="get all levels")
async def sokoban_all_levels_show(request: fastapi.Request):
    """
    [GET] method

    get all levels

    endpoint - /game/sokoban/all

    # returns
    ```json
    {
        data: [{...},{...}]
    }
    ```
    """
    games = await all(mongo)
    ret = []
    levels = games.copy()
    for x in games:
        game = await create(str(x["_id"]), levels)
        game["name"] = x["_id"]
        game["map"] = raw_creator(game["map"])
        game["map"] = render_perm(game)
        ret.append(game)
    return {"data":ret}


@app.get("/game/sokoban/all-raw",tags=["games endpoints"],summary="get all levels")
async def sokoban_all_levels_show_raw(request: fastapi.Request):
    """
    [GET] method

    get all levels raw data (not helpful for bot developers)

    endpoint - /game/sokoban/all-raw

    # returns
    ```json
    {
        ?
    }
    ```
    """
    games = await all(mongo)
    return games

@app.post("/game/sokoban/create-level",tags=["games endpoints"],summary="create sokoban level")
async def sokoban_level_thing_creator(request: fastapi.Request, le:sokobancreatelevelthing):
    """
    [POST] method

    create a new sokoban level

    endpoint - /game/sokoban/create-level

    # parameter

    - **level** - string that represent level eg (1111/1201/1301/1401, etc)
    - **name** - name of the level
    - **author** - author of the level

    # returns
    ```json
    {
        "sucess": "True/False",
    }
    ```
    """
    try:
        b = await name_checker(mongo ,le.name)
        if b:
            return {"success": "name already exists"}
        else:
            levels = {}
            levels["_id"] = le.name
            levels["map"] = le.level
            levels["played"] = 0
            levels["author"] = le.author
            await mongo["sokoban"]["levels"].insert_one(levels)
            return {"success": "True"}
    except:
        return {"success": "False"}

@app.post("/game/sokoban/action",tags=["games endpoints"],summary="action sokoban game")
async def push_the_box_action(request: fastapi.Request, action:sokobanaction):
    """
    [POST] method

    action a sokoban game

    endpoint - /game/sokoban/action

    # parameter

    - **game_id** - game token
    - **action** - action to do (left, right, up, down)

    # returns
    ```json
    {
        "win": "True/False if win or not",
        "board": "ready to use board",
    }
    ```
    """
    if action.action == "left":
        sokoban_currently_playing[action.game_id]["game"] = left(sokoban_currently_playing[action.game_id]["game"])
    elif action.action == "right":
        sokoban_currently_playing[action.game_id]["game"] = right(sokoban_currently_playing[action.game_id]["game"])
    elif action.action == "up":
        sokoban_currently_playing[action.game_id]["game"] = up(sokoban_currently_playing[action.game_id]["game"])
    elif action.action == "down":
        sokoban_currently_playing[action.game_id]["game"] = down(sokoban_currently_playing[action.game_id]["game"])
    return {"win":str(is_winning(sokoban_currently_playing[action.game_id]["game"])),"board":render_perm(sokoban_currently_playing[action.game_id]["game"])}

# endregion

# endregion

# region [games endpoints][akinator]

akinator_currently_playing = {}

@app.post("/game/akinator/create",tags=["games endpoints"],summary="create akinator game")
async def akinator_create_game(request: fastapi.Request, le:AkinatorCreate):
    """
    [POST] method.
    
    create your akinator game.

    # parameter
    - **language** - language of the game (en,en_animals,en_objects,ar,cn,de,de_animals,fr,jp,etc)

    # return
    ```json
    {
        "game_id": game-token,
        "question": "question asked by akinator",
        "confidence": "confidence level of akinator"
    }
    ```
    """
    game_id = str(uuid.uuid4())
    global akinator_currently_playing
    akii = await create_aki(le.language)
    akinator_currently_playing[str(game_id)] = {"game": akii}
    return {"game_id":str(game_id), "question": akii.question, "confidence":akii.progression}


@app.post("/game/akinator/close",tags=["games endpoints"],summary="akinator close")
async def akinator_game_close(request: fastapi.Request, gam:AkinatorGameClose):
    """
    [POST] method.
    
    Close your game after completion.    

    # parameter
    - **game_id** - game token

    # return
    ```json
    {
        "message": "thank you for playing!"
    }
    ```
    """
    akii:Akinator = akinator_currently_playing[gam.game_id]["game"]
    await akii.close()
    return {"message": "thanks for playing!"}

@app.post("/game/akinator/action",tags=["games endpoints"],summary="akinator action")
async def akinator_game_action(request: fastapi.Request, gam:AkinatorGameAction):
    """
    [POST] method.
    
    interact with your akinator game.

    # parameter
    - **game_id** - game token
    - **action** - action to do (**y**[yes], **n**[no] ,**idk**[i dont know],**p** [probably],**pn** [probably not])

    # return
    ```json
    {
        "question": "question",
        "step": "question number",
        "confidence":"percentage of game completion",
        "image": "if game complete",
        "description": "if game complete",
        "name": "if game complete",
        "pseudo": "if game complete",
        "ranking": "if game complete"
    }
    ```
    """
    if gam.action not in  ["y", "n", "idk", "p", "pn"]:
        return {"message": "wrong input"}
    akii:Akinator = akinator_currently_playing[gam.game_id]["game"]
    q = await akii.answer(gam.action)
    data = {"question": q, "step": akii.step, "confidence":akii.progression}
    if akii.progression >= 80:
        await akii.win()
        data["image"] = akii.first_guess["absolute_picture_path"]
        data["description"] = akii.first_guess["description"]
        data["name"] = akii.first_guess["name"]
        data["pseudo"] = akii.first_guess["pseudo"]
        data["ranking"] = akii.first_guess["ranking"]
    return data

# endregion

# region [image endpoints]
    
@app.get("/welcome",response_class=FileResponse, tags=["image endpoints"],summary="welcome card")
@limiter.limit("100/minute")
async def welcome_endpoint(request: fastapi.Request, background,message,text,avatar=None,username=None,userid=None):
    """
    welcome card<br>/welcome?background=https://cdn.discordapp.com/attachments/907213435358547968/974989177642950656/unknown.png&avatar=https://cdn.discordapp.com/attachments/907213435358547968/974989329858461766/unknown.png&message=welcome%20to%20my%20server&username=komi%20san&text=1000%20members%20now%20OWO<br>

    endpoint - /welcome

    # parameters
    - **background** - background image url
    - **avatar** - avatar image url
    - **message** - message to display
    - **text** - message to display in 3rd line
    - **username** - username to display
    - **userid** - userid to display (optional, use this and dont give username and avatar)

    # returns
    <img src="/asset/welcome.bmp">

    """
    if userid:
        info = await user_info(token,userid)
        avatar = info["avatar"]
        username = info["name"]

    a = await anyio.to_thread.run_sync(welcomer, {"background":background,"avatar":avatar,'username':username,'message':message,'text':text})
    return FileResponse(f"./trash/{a}.png")

@app.get("/level",response_class=FileResponse, tags=["image endpoints"],summary="level card")
@limiter.limit("100/minute")
async def level_endpoint(request: fastapi.Request, background,level:int,current_exp:int,max_exp:int,avatar=None,username=None,userid=None,bar_color="red", text_color="white"):
    """
    level card<br>/level?background=https://media.discordapp.net/attachments/992703788865572874/993888491756859423/20220705_223748.jpg&avatar=https://cdn.discordapp.com/avatars/750265172488224788/a180ee0b4a3ec01f676491798460200d.png?size=4096&username=Yumi&discriminator=1000&current_exp=276&max_exp=454&level=8&bar_color=%23FFA0D0&text_color=%23c2648d<br>    
 
    endpoint - /level

    # parameters
    - **background** - background image url
    - **avatar** - avatar image url
    - **username** - username to display
    - **current_exp** - current exp
    - **max_exp** - max exp
    - **level** - level
    - **bar_color** - bar color (color name or hex)
    - **text_color** - text color (color name or hex)

    # returns
    <img src="https://cdn.discordapp.com/attachments/907213435358547968/994620579816681572/unknown.png">

    """

    if userid:
        info = await user_info(token,userid)
        avatar = info["avatar"]
        username = info["name"]
    a = await anyio.to_thread.run_sync(level_maker , {'background':background,'level':level,'avatar':avatar,'username':username,'current_exp':current_exp,'max_exp':max_exp,'bar_color':bar_color,'text_color':text_color})
    return FileResponse(f"./trash/{a}.png")


@app.get("/rip",response_class=FileResponse, tags=["image endpoints"],summary="rip my g")
@limiter.limit("100/minute")
async def rip_endpoint(request: fastapi.Request, avatar):
    """
    rip avatar<br>/rip?avatar=https://cdn.discordapp.com/attachments/907213435358547968/974990788972916766/unknown.png<br>

    endpoint - /rip

    # parameters
    - **avatar** - avatar image url


    # returns
    <img src="/asset/rip.bmp">

    """

    a = await anyio.to_thread.run_sync(rip_maker ,avatar)    
    return FileResponse(f"./trash/{a}.png")


@app.get("/wap",response_class=FileResponse, tags=["image endpoints"],summary="spongebob pray")
@limiter.limit("100/minute")
async def wap_endpoint(request: fastapi.Request, avatar):
    """
    spongebob pray<br>/wap?avatar=https://cdn.discordapp.com/attachments/907213435358547968/974989177642950656/unknown.png<br>

    endpoint - /wap

    # parameters
    - **avatar** - avatar image url


    # returns
    <img src="/asset/wap.bmp">

    """

    a = await anyio.to_thread.run_sync(spongebobWAP ,avatar)    
    return FileResponse(f"./trash/{a}.png")



@app.get("/throwthechild",response_class=FileResponse, tags=["image endpoints"],summary="throw child")
@limiter.limit("100/minute")
async def throwchild_endpoint(request: fastapi.Request, avatar):
    """
    THROW THE CHILD!<br>/throwthechild?avatar=https://cdn.discordapp.com/attachments/907213435358547968/974990788972916766/unknown.png<br>

    endpoint - /throwthechild

    # parameters
    - **avatar** - avatar image url

    # returns
    <img src="/asset/throw.bmp">
    """
    a = await anyio.to_thread.run_sync(throwthechild ,avatar)
    return FileResponse(f"./trash/{a}.png")

burn = aioify(obj=burning)

@app.get("/burn",response_class=FileResponse, tags=["image endpoints"],summary="burn avatar")
@limiter.limit("100/minute")
async def burnchild(request: fastapi.Request, avatar):
    """
    BURN THE CHILD!<br>/burn?avatar=https://cdn.discordapp.com/attachments/907213435358547968/974990788972916766/unknown.png<br>

    endpoint - /burn

    # parameters
    - **avatar** - avatar image url

    # returns
    <img src="/asset/burn.bmp">

    """

    a = await anyio.to_thread.run_sync(burning ,avatar)
    return FileResponse(f"./trash/{a}.png")


@app.get("/tear",response_class=FileResponse, tags=["image endpoints"],summary="spongebob tear")
@limiter.limit("100/minute")
async def spongebobtear_endpoint(request: fastapi.Request, avatar1,avatar2):
    """
    tear of happiness<br>/tear?avatar1=https://cdn.discordapp.com/attachments/907213435358547968/974990788972916766/unknown.png&avatar2=https://cdn.discordapp.com/attachments/907213435358547968/974989329858461766/unknown.png<br>

    endpoint - /tear

    # parameters
    - **avatar1** - avatar image url
    - **avatar2** - avatar image url

    # returns
    <img src="/asset/tear.bmp">
    """
    a = await anyio.to_thread.run_sync(tear ,{"avatar1":avatar1,"avatar2":avatar2})
    return FileResponse(f"./trash/{a}.png")


@app.get("/discordsays",response_class=FileResponse, tags=["image endpoints"],summary="discordsays")
@limiter.limit("100/minute")
async def discorsays_endpoint(request: fastapi.Request, message,userid=None,avatar=None,username=None,hex=None,color="#ededed",time="Today at 03:00 AM"):
    """
    make fake discord messages<br>/discordsays?avatar=https://cdn.discordapp.com/attachments/907213435358547968/974989329858461766/unknown.png&username=komi+san&message=i+like+tadano+san&time=Today+at+2%3A22+AM<br>

    endpoint - /discordsays

    # parameters
    - **avatar** - avatar image url
    - **username** - username
    - **message** - message
    - **time** - time (default: Today at 03:00 AM)
    - **hex** - hex color (default: #ededed)
    - **color** - color (default: #ededed)
    - **userid** - userid (optional)
    

    # returns
    <img src="/asset/discordsays.bmp">

    """
    if hex is not None:
        hex = "#" + hex
    if userid is not None:
        info = await user_info(token,userid)
        avatar = info["avatar"]
        username = info["name"]
    a = await anyio.to_thread.run_sync(discordsays ,{'avatar':avatar,'username':username,'message':message,'color':(hex or color),'time':time})
    return FileResponse(f"./trash/{a}.png")


@app.get("/love-me",response_class=FileResponse, tags=["image endpoints"],summary="love calc")
@limiter.limit("100/minute")
async def lovemeeee_endpoint(request: fastapi.Request, avatar1:str, avatar2:str, percentage:int=None):
    """
    random love calculator<br>/love-me?avatar1=https://cdn.discordapp.com/attachments/907213435358547968/974989329858461766/unknown.png&avatar2=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<br>

    endpoint - /love-me

    # parameters
    - **avatar1** - avatar image url
    - **avatar2** - avatar image url
    - **percentage** - fixed percentage
    

    # returns
    <img src="/asset/loveme.png">

    """
    a = await anyio.to_thread.run_sync(lover_me ,{"avatar1":avatar1,"avatar2":avatar2,"percentage":percentage})
    return FileResponse(f"./trash/{a}.png")

@app.get("/coat",response_class=FileResponse, tags=["image endpoints"],summary="wear a coat")
@limiter.limit("100/minute")
async def coatcoat_endpoint(request: fastapi.Request, avatar:str):
    """
    make your avatar wear a cozy coat<br>/coat?avatar=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<br>

    endpoint - /coat

    # parameters
    - **avatar** - avatar image url
    

    # returns
    <img src="/asset/coatfinal.png">

    """
    a = await anyio.to_thread.run_sync(coat_maker ,avatar)
    return FileResponse(f"./trash/{a}.png")


@app.get("/uwu",response_class=FileResponse, tags=["image endpoints"],summary="uwu")
@limiter.limit("100/minute")
async def uwu_avatar_endpoint(request: fastapi.Request, avatar:str):
    """
    uwu your avatar<br>/uwu?avatar=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<br>

    endpoint - /uwu

    # parameters
    - **avatar** - avatar image url
    
    # returns
    <img src="/asset/uwufinal.png">

    """
    a = await anyio.to_thread.run_sync(uwu_maker ,avatar)
    return FileResponse(f"./trash/{a}.png")

@app.get("/leaderboard",response_class=FileResponse, tags=["image endpoints"],summary="leaderboard card")
@limiter.limit("100/minute")
async def leaderboard_endpoint(
    request: fastapi.Request,
    background:str,
    serverlogo:str,
    pos1:str=None,
    pos2:str=None,
    pos3:str=None,
    pos4:str=None,
    pos5:str=None,
    pos6:str=None,
    pos7:str=None,
    pos8:str=None,
    pos9:str=None,
    pos10:str=None
    ):
    """
    leaderboard card for your leveling system<br>/leaderboard?background=https://cdn.discordapp.com/attachments/907213435358547968/994600232161656892/unknown.png&serverlogo=https://cdn.discordapp.com/attachments/907213435358547968/994595322917556344/unknown.png&pos1=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000&pos2=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000&pos3=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000&pos4=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000&pos5=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000&pos6=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000&pos7=https://cdn.discordapp.com/attachments/907213435358547968/992384949401432094/fddf655fb40613d2.png<sep>resetxd<sep>level+1+%7C+exp+2000<br>

    endpoint - /leaderboard

    **note**: use of \<sep> is important

    # parameters
    - **serverlogo** - logo of the server *required 
    - **pos1** - content related to pos1 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos2** - content related to pos2 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos3** - content related to pos3 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos4** - content related to pos4 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos5** - content related to pos5 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos6** - content related to pos6 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos7** - content related to pos7 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos8** - content related to pos8 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos9** - content related to pos9 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 
    - **pos10** - content related to pos10 eg (avatarurl\<sep>username\<sep>level 1 | exp 100) 

    # returns
    <img src="/asset/leaderme.png">

    """
    a = await anyio.to_thread.run_sync(
        leaderboardCreator,
        {"background":background,
        "serverlogo":serverlogo,
        "pos1":pos1,
        "pos2":pos2,
        "pos3":pos3,
        "pos4":pos4,
        "pos5":pos5,
        "pos6":pos6,
        "pos7":pos7,
        "pos8":pos8,
        "pos9":pos9,
        "pos10":pos10}
        )
    return FileResponse(f"./trash/{a}.png")

# endregion

# region [gif endpoints]

@app.get("/triggered.gif",response_class=FileResponse, tags=["gif endpoints"],summary="triggered")
@limiter.limit("100/minute")
async def triggered(request: fastapi.Request, avatar:str, intensity:int= 10):
    """
    make triggered gif meme with variable intensity<br>/triggered.gif?avatar=https://cdn.discordapp.com/avatars/424133185123647488/08d40e3db4b21b887720d649dacc0f5c.png?size=1024<br>

    endpoint - /triggered.gif

    # parameters
    - **avatar** - avatar image url
    - **intensity** - the intensity of trigger [not required]

    # returns
    <img src="/asset/triggered.gif">

    """
    avatar = avatar.replace(".gif",".png")
    a = await anyio.to_thread.run_sync(trigger_maker ,{"avatar":avatar,"intensity":intensity})
    return FileResponse(f"./trash/{a}.gif")

# endregion

# region [premium endpoints]

@app.get("/balance-card", response_class=FileResponse, include_in_schema=False)
@limiter.limit("100/minute")
async def prem_bal_card(request: fastapi.Request, id: str):
    with open("./tempdata/tempbalance.json", "r") as file:
        data = jsonlib.load(file)
        a = prem_balance(data[id])
    return FileResponse(f"./trash/{a}.png") 

@app.post("/premium/balance-card",response_class=JSONResponse, tags=["premium endpoints"],summary="balance card")
@limiter.limit("100/minute")
async def premium_blance_card(request: fastapi.Request, bal:BalanceCard):
    try:
        search = await mongo.users.users.find_one({"token": bal.token})
        if search == None:
            return {"success": "invalid token"}
        user = mongo[search["_id"]]
        if not premium_user_checker(token, user):
            return {"message": "access denied"}
    except:
        return {"message": "access denied"}

    with open("./tempdata/tempbalance.json", "r") as file:
        data = jsonlib.load(file)
        tok = secrets.token_urlsafe(16)
        data[tok] = {
            "avatar": bal.avatar,
            "background": bal.background,
            "username": bal.username,
            "balanceimage": bal.balanceimage,
            "balancetext": bal.balancetext,
            "balance": bal.balance,
            "banktext": bal.banktext,
            "bankimage": bal.bankimage,
            "bank": bal.bank,
            "totaltext": bal.totaltext,
            "totalimage": bal.totalimage,
            "total": bal.total
        }
    with open("./tempdata/tempbalance.json", "w") as file:
        jsonlib.dump(data, file, indent=4)
    
    return {"image":f"https://api.resetxd.xyz/balance-card?id={tok}"}



@app.get("/overlay-card", response_class=FileResponse, include_in_schema=False)
@limiter.limit("100/minute")
async def prem_bal_card(request: fastapi.Request, id: str):
    with open("./tempdata/tempbalance.json", "r") as file:
        data = jsonlib.load(file)
        a = prem_overlay(data[id])
    return FileResponse(f"./trash/{a}.png") 


@app.post("/premium/overlays",response_class=JSONResponse, tags=["premium endpoints"],summary="overlays")
@limiter.limit("100/minute")
async def premium_overlays_card(request: fastapi.Request, ov:OverlayCards):
    """
    [POST] 
    
    add any overlay to your api and make your own memes with them!

    # parameters
    - **token** - token that can be registered through homepage
    - **avatar** - avatar image url
    - **overlay** - overlay image url, must have transparent background

    # returns
    this is an example of how the overlay card will look like but doesnt only restrict to this overlay <br>
    <img src= "/asset/overlayfinal.png">
    
    """
    try:
        search = await mongo.users.users.find_one({"token": ov.token})
        if search == None:
            return {"success": "invalid token"}
        user = mongo[search["_id"]]
        if not premium_user_checker(token, user):
            return {"message": "access denied"}
    except:
        return {"message": "access denied"}

    with open("./tempdata/tempbalance.json", "r") as file:
        data = jsonlib.load(file)
        tok = secrets.token_urlsafe(16)
        data[tok] = {
            "avatar": ov.avatar,
            "overlay": ov.overlay
        }
    with open("./tempdata/tempbalance.json", "w") as file:
        jsonlib.dump(data, file, indent=4)
    
    return {"image":f"https://api.resetxd.xyz/overlay-card?id={tok}"}


# endregion