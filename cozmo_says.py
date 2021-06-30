import sqlite3
from sqlite3 import Error
import cozmo
import asyncio

import random
import threading
from datetime import datetime, timedelta
import time
from cozmo.objects import LightCube1Id, LightCube2Id, LightCube3Id


# Creates a database connection
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    return conn


# DATABASE STUFF
def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        zeiger = conn.cursor()
        zeiger.execute(create_table_sql)
    except Error as e:
        print(e)


# Writes Data in Database
def writeInDatabase(conn, currentGame, vorname):
    currentGame.gameEnd = datetime.now()
    conn.execute("""
            INSERT INTO cozmosays
                    VALUES (?,?,?,?,?)
            """,
                 (vorname, currentGame.gameStart, currentGame.gameEnd, currentGame.gameRoundCounter,
                  currentGame.gamehighscore)
                 )
    conn.commit()
    conn.close()


# Cozmo_programm
def cozmo_program(robot: cozmo.robot.Robot):
    # where the database shall be located
    database = "C:/Users/velme/Cozmo/examples/tutorials/01_basics/CozmoDatabase.db"
    # table information
    sql_create_projects_table = """
        CREATE TABLE IF NOT EXISTS cozmosays (
        vorname VARCHAR(20), 
        gameStart DATE,
        gameEnd DATE,
        gameRoundCounter INTEGER,
        highscore INTEGER
        );"""

    # create a database connection
    conn = create_connection(database)
    # create tables
    if conn is not None:
        # create personen table
        create_table(conn, sql_create_projects_table)

    else:
        print("Error! cannot create the database connection.")
    global vorname
    # set cubeobjects(Cozmo API)
    cube1 = robot.world.get_light_cube(LightCube1Id)
    cube2 = robot.world.get_light_cube(LightCube2Id)
    cube3 = robot.world.get_light_cube(LightCube3Id)
    # event to be used later
    event = threading.Event()
    # list of gameobjects used later to build a random array
    gameobjects = [1, 2, 3]
    t = datetime.now()
    # wintext list
    wintext = ["Das war super! ", "Toll gemacht! ", "Sehr gut! "]
    #
    robot.world.enable_block_tap_filter(enable=False)
    robot.move_lift(-3)

    """Robot turns his Head and tries to recognise Faces and turns his head. If Cozmo finds a Face which is in his Database,
    the global variable "vorname" is set to the name of the face.(Cozmo API and Tutorials)"""
    robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
    face = None
    while face == None or not face.name:
        turn_action = None
        if face:
            # start turning towards the face
            turn_action = robot.turn_towards_face(face)

        if not (face and face.is_visible):
            # find a visible face, timeout if nothing found after a short while
            try:
                face = robot.world.wait_for_observed_face(timeout=30)
                print("Found face", face)
            except asyncio.TimeoutError:
                print("Didn't find a face - :-( !")
                return

        if turn_action:
            # Complete the turn action if one was in progress
            turn_action.wait_for_completed()

        time.sleep(.1)
    try:
        vorname = face.name
    except not face.name:
        print("this should not be possible")

    # class Cubemoved. Contains variables for the gamelogic
    class Cubemoved(object):
        last_cube_moved = 0
        objectmoved = False
        wasright = True
        gameon = True
        bluecube = 0
        redcube = 0
        greencube = 0

        def __init__(self):
            self.last_cube_moved = 0
            self.objectmoved = False
            self.wasright = True
            self.gameon = True
            self.bluecube = 0
            self.redcube = 0
            self.greencube = 0

    cubemoved = Cubemoved()

    # class Gamestats. Contains Gamesession Data, which will be written in the table after the game is over
    class GameStats(object):
        gameLevel = 1
        gameStart = datetime.now()
        gameEnd = datetime.now()
        gameRoundCounter = 0
        gamehighscore = 0
        maxLevel = 10

        # The class "constructor" - It's actually an initializer
        def __init__(self, gameLevel, gameStart):
            self.gameLevel = gameLevel
            self.gameStart = gameStart
            self.gameEnd = datetime.now()
            self.gameRoundCounter = 0
            self.gamehighscore = 0
            self.maxLevel = 10

    # make_gameStats creates a Gamestatsobject named currentgame
    def make_gameStats(gameLevel, t):
        currentGame = GameStats(gameLevel, t)
        return currentGame

    currentGame = make_gameStats(1, t)

    # This will be called whenever an EvtObjectTappingStarted event is dispatched -
    # whenever we detect a cube was tapped
    # sets the objectmoved to True
    # sets the last_cube_moved the the objectid of the Cube was tapped
    # sets the event, part of the threading Thread
    # executes cube_off function to turn cubelights off
    def handle_object_tapping_started(evt, **kw):
        print("Object %s was tapped"
              % evt.obj.object_id)
        cubemoved.objectmoved = True
        cubemoved.last_cube_moved = evt.obj.object_id
        event.set()
        cube_off()

    # Function that lights the cube. A value as Int is needed. The value defines which cube will be lightened
    # value will be compared to the 3 cubes saved in the cubemoved object and the cube == value will be lightened
    # the other cubes will be turned off
    # cube.set_lights is part of the cozmo API
    def light_cube(value):
        if value == cubemoved.bluecube:
            cube1.set_lights(cozmo.lights.blue_light)
            cube2.set_lights(cozmo.lights.off_light)
            cube3.set_lights(cozmo.lights.off_light)
        if value == cubemoved.redcube:
            cube2.set_lights(cozmo.lights.red_light)
            cube1.set_lights(cozmo.lights.off_light)
            cube3.set_lights(cozmo.lights.off_light)
        if value == cubemoved.greencube:
            cube3.set_lights(cozmo.lights.green_light)
            cube1.set_lights(cozmo.lights.off_light)
            cube2.set_lights(cozmo.lights.off_light)

    # Function will turn off all cubes
    # cube.set_lights is part of the cozmo API
    def cube_off():
        cube1.set_lights(cozmo.lights.off_light)
        cube2.set_lights(cozmo.lights.off_light)
        cube3.set_lights(cozmo.lights.off_light)

    # function which compares the value with the last_cube_moved of the cubemoved object
    # the roboteventhandler is used. There is an event added, which will be triggered if a cube is tapped.
    # if theres no event triggered after 5 seconds the programm will close and the data of this game session will be safed in the database
    # if the input == last_cube_moved, the cubemoved.wasright= True. the light_cube function is called and after a 0.5 second sleep the cube_off function is called.
    # so the cube blinks to give the feedback it was tapped
    # if the value!=cubemoved.lastcubemoved, cubemoved.wasright= False and Cozmo plays a lose animation(cozmo API)
    # at the end the event is cleared and cubemoved.objectmoved = False
    def checkinput(value):
        robot.add_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)

        event.wait(timeout=5)

        robot.remove_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        if cubemoved.objectmoved:
            if value == cubemoved.last_cube_moved:
                print("richtig")
                cubemoved.wasright = True
                light_cube(value)
                time.sleep(0.5)
                cube_off()
            else:
                print(value)
                print("falsch")
                robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceLoseRound).wait_for_completed()
                cubemoved.wasright = False
        else:
            writeInDatabase(conn, currentGame, vorname)
            exit()

        cubemoved.objectmoved = False
        event.clear()

    # this function sets the cubes right. The cubes will light and the user has to tap it to assign the object ids to the lightened cubes
    # the cubes will light up after another in their colors. if the first cube was tapped, the id of the cube will be assigned to the color.
    # After a tap of the lightened cube, the cube turns off and the next cube will light up. Cozmo says: "Berühre den leuchtenden Würfel"
    # like in the function above the roboteventhandler and the event.wait and event.clear is used to track the tap
    def testcubes():

        cube1.set_lights(cozmo.lights.blue_light)
        robot.add_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        robot.say_text("Berühre den leuchtenden Würfel", use_cozmo_voice=False,
                       duration_scalar=0.6).wait_for_completed()
        event.wait()
        robot.remove_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        cubemoved.bluecube = cubemoved.last_cube_moved
        cube_off()
        event.clear()
        cube2.set_lights(cozmo.lights.red_light)
        robot.add_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        robot.say_text("Berühre den leuchtenden Würfel", use_cozmo_voice=False,
                       duration_scalar=0.6).wait_for_completed()
        event.wait()
        robot.remove_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        cubemoved.redcube = cubemoved.last_cube_moved
        cube_off()
        event.clear()
        cube3.set_lights(cozmo.lights.green_light)
        robot.add_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        robot.say_text("Berühre den leuchtenden Würfel", use_cozmo_voice=False,
                       duration_scalar=0.6).wait_for_completed()
        event.wait()
        robot.remove_event_handler(cozmo.objects.EvtObjectTapped, handle_object_tapping_started)
        cubemoved.greencube = cubemoved.last_cube_moved
        cube_off()
        event.clear()
        cubemoved.objectmoved = False

    # this functions lights up the cubes 3 times in a row in following Order: Blue, Green, Red
    # a small functions used as a intro to the game
    def gameintrocubes():
        for i in range(3):
            light_cube(1)
            time.sleep(0.2)
            light_cube(2)
            time.sleep(0.2)
            light_cube(3)
            time.sleep(0.2)
        cube_off()
        time.sleep(0.5)
    # this is the mainprogram
    # User gets introduced and the gameintrocube function is called
    # to track the tapped events a threading.Thread(target=testcubes()) is started
    # while cubemoved.gameon == True, the game will move on if its not cancelled by non-input
    # if the maxlevel is reached the game will cancel and data will be saves
    # else the cubearray[] will be filled depending on how high the game level is. For every gamelevel reached a new integer will be added to the array
    # Depending on the gamelevel the difficulty will raise. if the gamelevel is below 3 the cubes will light for 3 seconds and the pause between the lightened cubes is 1.5 seconds
    # if the gamelevel is between 3 and 5 the time will decrease to 2 secondes lightened und 1 second pause
    # if the gamelevel is over 5 the time will decrease to 1 second lightened and 0.5 secounds pause
    # at first the cozmo will lighten up the cubes through running through the randomly generated array
    # after the first runthrough its time to check the users input.
    # in the second runthrough an input is expected. a second thread is started with the target= checkinput() and input will be compared with the actual element of the array
    # if the cubemoved.wasright the next element will be checked. if cubemoved.wasright after the runthrough of the array, the level will be increased.
    # if !cubemoved.wasright the gamelevel will set to 1.
    # by successfully beaten a level. Cozmo will cheer and praise the user.
    # although the highscore will be checked after completing a gamelevel. if the gamelevel is higher than the actual highscore of this session. highscore=gamelevel
    def robotmain():
        robot.say_text("Hallo " + vorname + " Willkommen zu Cozmo Says", use_cozmo_voice=False,
                       duration_scalar=0.6).wait_for_completed()
        gameintrocubes()
        t2 = threading.Thread(target=testcubes())
        t2.start()
        cube_array = []
        while cubemoved.gameon:
            if currentGame.gameLevel == currentGame.maxLevel:
                robot.say_text("Herzlichen Glückwunsch du hast das höchste Level erreicht!", use_cozmo_voice=False,
                               duration_scalar=0.6).wait_for_completed()
                writeInDatabase(conn, currentGame, vorname)
                exit()

            else:
                cube_array.append(random.choice(gameobjects))
                robot.say_text("Wir befinden uns in Level %d" % currentGame.gameLevel, use_cozmo_voice=False,
                               duration_scalar=0.6).wait_for_completed()
                robot.say_text("Ich fange an!", use_cozmo_voice=False, duration_scalar=0.6).wait_for_completed()

                if currentGame.gameLevel < 3:
                    for i in range(len(cube_array)):
                        light_cube(cube_array[i])
                        time.sleep(3)
                        cube_off()
                        time.sleep(1.5)
                if 2 < currentGame.gameLevel <= 5:
                    for i in range(len(cube_array)):
                        light_cube(cube_array[i])
                        time.sleep(1.5)
                        cube_off()
                        time.sleep(1)
                if currentGame.gameLevel > 5:
                    for i in range(len(cube_array)):
                        light_cube(cube_array[i])
                        time.sleep(1)
                        cube_off()
                        time.sleep(0.5)
                robot.say_text("Du bist dran", use_cozmo_voice=False, duration_scalar=0.6).wait_for_completed()
                for i in range(len(cube_array)):
                    if cubemoved.wasright:
                        t1 = threading.Thread(target=checkinput(cube_array[i]))
                        t1.start()
                    else:
                        break
                if cubemoved.wasright:
                    robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceWinSession).wait_for_completed()
                    currentGame.gameLevel = currentGame.gameLevel + 1
                    if currentGame.gamehighscore < currentGame.gameLevel - 1:
                        currentGame.gamehighscore = currentGame.gameLevel - 1
                    robot.say_text(random.choice(wintext) + vorname, use_cozmo_voice=False,
                                   duration_scalar=0.6).wait_for_completed()
                    print("gewonnen")
                else:
                    robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceLoseSession).wait_for_completed()
                    currentGame.gameLevel = currentGame.gameLevel - 1
                    robot.say_text("Schade, du hast es bis Level %d geschafft."
                                   " Versuche es nochmal" % currentGame.gameLevel, use_cozmo_voice=False,
                                   duration_scalar=0.6).wait_for_completed()
                    currentGame.gameLevel = 1
                    cube_array.clear()
                    cubemoved.wasright = True
                time.sleep(2)
                currentGame.gameRoundCounter = currentGame.gameRoundCounter + 1

    robotmain()


cozmo.run_program(cozmo_program)
