#!/usr/bin/env python3



import asyncio
from logging import Handler
import time
import sqlite3
from sqlite3 import Error
from datetime import datetime

import cozmo
import random
from cozmo.objects import LightCube1Id, LightCube2Id


#DATABASE STUFF
#connect to database file/ create if it does not exist yet
# throws exception if connection can't be established
def create_connection(db_file):
    """ create a database connection to a SQLite CozmoDatabase """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    
    return conn

#DATABASE STUFF
#create a table using the connection (conn) and the sql statement 'create_table_sql'
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

# writes the data of the currentgame instance into the database and closes the connection to the database
def writeInDatabase(conn, currentGame, vorname):
    currentGame.gameEnd = datetime.now()
    conn.execute("""
            INSERT INTO tonHoehen 
                    VALUES (?,?,?,?,?)
            """, 
            (vorname, currentGame.gameStart, currentGame.gameEnd, currentGame.gameRoundMistakes, currentGame.gameLevel)
            )
    conn.commit()
    conn.close()


#main program, that's where the magic happens
#calls writeInDatabase, create_table & create_connection
# has a class GameStats and will create an instance of it called currentGame
def cozmo_program(robot: cozmo.robot.Robot):
    #DATABASE STUFF
    #where the database shall be located
    database = "C:/Users/Marnick/Documents/Cozmo/cozmo_sdk_examples_1.4.10/tutorials/01_basics/CozmoDatabase.db"
    #the name of the table to write in and it's collums
    sql_create_projects_table = """
    CREATE TABLE IF NOT EXISTS tonHoehen (
    vorname VARCHAR(20), 
    gameStart DATE,
    gameEnd DATE,
    gameRoundMistakes INTEGER,
    reachedLevel INTEGER
    );"""

    # create a database connection
    conn = create_connection(database)
    # create tables
    if conn is not None:
    # create table tonHoehen 
        create_table(conn, sql_create_projects_table)

    else:
        print("Error! Can not create the database connection.")
    #DATABASE STUFF ends here (for now)

    ####FACERECOGNITION, will be in endless loop if user isn't in Cozmos userDatabase
# Cozmo API commands to lift Cozmos head up and the lift down, to make face recognition easier
    robot.move_lift(-3)
    robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

    # initialize face with none 
    face = None

    # this loop will continue as long as face is none or the face cozmo recognises has no face.name (is not recognized as a face from Cozmos database)
    while face == None or not face.name:
        #to make Cozmo "follow" a face, to increase the probability to recognise a face, the turn_action is used
        turn_action = None
        if face:
# start turning towards the face, Cozmo API command 
            turn_action = robot.turn_towards_face(face)

#Cozmo API command face.is_visible is used to check if there is a face currently visible for Cozmo
        if not (face and face.is_visible):
            # find a visible face, timeout if nothing found after 30 seconds
            try:
#Cozmo API command robot.world.wait_for_observed_face(timeout=30)
                # set face to the face cozmo is observing, if he is not observing a face within 30 seconds, the try fails 
                face = robot.world.wait_for_observed_face(timeout=30)
                print("Found face", face)
            except asyncio.TimeoutError:
                print("Didn't find a face - :-( !")
                return

        if turn_action:
# Complete the turn action if one was in progress using the Cozmo API command wait_for_completed() on turn_action
            turn_action.wait_for_completed()
# Cozmo API command, wait for 1 second
        time.sleep(.1)
    try:
# Cozmo API provides a name for a face, if the face is in Cozmos database
        # try to use the name, if the face is not in Cozmos database (or Cozmo does not recognise it correctly) the try fails
        vorname = face.name
    except not face.name:
        print("this should not be possible")
    #FACERECOGNITION part ends here

    #Class to store game related data
    # gameLevel: current level, correctAnswers: correct answers in total while wrong ansers decrease the correct answers
    #gameStart: when this game started
    #gameEnd: when the game is over (win or quit)
    #cube1Tapped: boolean for flagging if cube 1 was tapped
    #cube2Tapped: boolean for flagging if cube 2 was tapped
    class GameStats(object):
        gameLevel = 1
        correctAnswers = 0
        gameStart = datetime.now()
        gameEnd = datetime.now()
        gameRoundMistakes = 0
        cube1Tapped = False
        cube2Tapped = False
        # The class "constructor" - It's actually an initializer 
        def __init__(self, gameLevel, correctAnswers, gameStart):
            self.gameLevel = gameLevel
            self.correctAnswers = correctAnswers
            self.gameStart = gameStart
            self.gameEnd = datetime.now()
            self.gameRoundMistakes = 0


    t = datetime.now()
    # methode to make an instance of the gameStats class
    def make_gameStats(gameLevel, correctAnswers, t):
        currentGame = GameStats(gameLevel, correctAnswers, t)
        return currentGame
    
    # currentGame: instance of the gameStats class with the current time as GameStart time, 0 mistakes and Level one (since that's where we start)
    currentGame = make_gameStats(1, 0, t)


# allnoteslist: a list of all SongNote objects, consisting of all notes from C2 to C3_Sharp (Cozmo API Objects in an ordinary dictionary)
    allnoteslist = [cozmo.song.NoteTypes.C2, 
                cozmo.song.NoteTypes.C2_Sharp, cozmo.song.NoteTypes.D2, 
                cozmo.song.NoteTypes.D2_Sharp, cozmo.song.NoteTypes.E2,
                cozmo.song.NoteTypes.F2, cozmo.song.NoteTypes.F2_Sharp,
                cozmo.song.NoteTypes.G2, cozmo.song.NoteTypes.G2_Sharp,
                cozmo.song.NoteTypes.A2, cozmo.song.NoteTypes.A2_Sharp,
                cozmo.song.NoteTypes.B2, cozmo.song.NoteTypes.C3,
                cozmo.song.NoteTypes.C3_Sharp]


    #gameOn: boolean for flagging if the main game loop shall continue
    gameOn = True
# Cozmo API command, make Cozmo say text in a (more) human voice
    robot.say_text("Willkommen zu, finde den höheren Ton!", use_cozmo_voice=False,
                   duration_scalar=0.6).wait_for_completed()

######################################################### MAIN GAME LOOP STARTS HERE########################################################
    while gameOn:

        # depending on the level the distance between the notes is calculated, while the first note is random
        # the secon note is closer if the level is higher
        if currentGame.gameLevel == 1:
            # random_note1 is picked randomly amog the 6 lowest notes possible
            random_note1 = random.randint(0, 5)
            print(random_note1)
            # to be easier distiguishable random_note2 as to be atleast 6 half notes away from random_note1
            random_note2 = random_note1 + random.randint(6, 7)
            print(random_note2)
        if currentGame.gameLevel == 2:
            random_note1 = random.randint(0, 7)
            print(random_note1)
            random_note2 = random_note1 + random.randint(4, 5)
            print(random_note2)
        if currentGame.gameLevel == 3:
            random_note1 = random.randint(0, 9)
            print(random_note1)
            random_note2 = random_note1 + random.randint(1, 3)
            print(random_note2)

   
    # noteoptionsdict: all 2 notes are in a dictionary now, the lowest note has the key 1 and the higest has the key 2
        noteoptionsdict = {1: allnoteslist[random_note1], 2: allnoteslist[random_note2]}
    # listOfShuffledOptions: list of all keys of noteoptionsdict
        listOfShuffledOptions = list(noteoptionsdict.keys())
    # listOfShuffledOptions gets shuffeled
        random.shuffle(listOfShuffledOptions)
        random.shuffle(listOfShuffledOptions)
        random.shuffle(listOfShuffledOptions)
        print("shuffeled list: ", listOfShuffledOptions)



#inicialize the cubes, Cozmo API command
        cube1 = robot.world.get_light_cube(LightCube1Id)  # looks like a paperclip
        cube2 = robot.world.get_light_cube(LightCube2Id)  # looks like a lamp / heart


        note1 = [
# putting one note (shuffled order) and a half note of rest in a song called note1 using the Cozmo API command 'cozmo.song.SongNote'
            cozmo.song.SongNote(allnoteslist[listOfShuffledOptions[0]], cozmo.song.NoteDurations.Half),
            cozmo.song.SongNote(cozmo.song.NoteTypes.Rest, cozmo.song.NoteDurations.Half) ]

        note2 = [
# putting one note (shuffled order) and a half note of rest in a song called note2 using the Cozmo API command 'cozmo.song.SongNote'
            cozmo.song.SongNote(allnoteslist[listOfShuffledOptions[1]], cozmo.song.NoteDurations.Half),
            cozmo.song.SongNote(cozmo.song.NoteTypes.Rest, cozmo.song.NoteDurations.Half) ]

  

        # turn on light of a cube and Play note, then turn cube light off
        if cube1 is not None:
#Cozmo API command to turn on a light cube (red light)
            cube1.set_lights(cozmo.lights.red_light)
        else:
#Cozmo API command for logger warning, if something goes wrong with the cube
            cozmo.logger.warning("Cozmo is not connected to a LightCube1Id cube - check the battery.")

#Cozmo API command to play notes
        robot.play_song(note1, loop_count=1).wait_for_completed()
#Cozmo API command to turn the light cube off
        cube1.set_lights_off()
#Cozmo API command to wait a second
        time.sleep(1)

    # turn on light of other cube and Play note, then turn cube light off
        if cube2 is not None:
             #Cozmo API command to turn on a light cube (blue light)
            cube2.set_lights(cozmo.lights.blue_light)
        else:
             #Cozmo API command for logger warning, if something goes wrong with the cube
            cozmo.logger.warning("Cozmo is not connected to a LightCube2Id cube - check the battery.")
#Cozmo API command to play notes
        robot.play_song(note2, loop_count=1).wait_for_completed()
        #Cozmo API command to turn the light cube off
        cube2.set_lights_off()
        #Cozmo API command to wait a second
        time.sleep(1)

        #Just in case the events might be needed later, they are stored here
#Cozmo API command robot.world.wait_for(cozmo.objects.EvtObjectTapped, timeout=30)
        try:
            eventX = robot.world.wait_for(cozmo.objects.EvtObjectTapped, timeout=30)
        except:
            #if there is no event detected after 30 seconds, write in database and exit the program
            writeInDatabase(conn, currentGame, vorname)
            exit()
        print(eventX.obj)

        #Check wich cube was tapped + Game logic
#Cozmo API object event and it's property obj is used here to check if the event was on cube1
        if ((eventX is not None) and (cube1 == eventX.obj)):
            # if cube1 was tapped, set currentGame.cube1Tapped to true
            currentGame.cube1Tapped = True
            print("true man")
#Cozmo API object event and it's property obj is used here to check if the event was on cube1
        if ((eventX is not None) and (cube2 == eventX.obj)):
        # if cube2 was tapped, set currentGame.cube2Tapped to true
            currentGame.cube2Tapped = True
            print("all the same")
        if (currentGame.cube1Tapped):
            print("cube 1 was tapped ", listOfShuffledOptions[0])
            # set currentGame.cube1Tapped back to false
            currentGame.cube1Tapped = False
            #check if the note assosiated with cube1 has the key 2 (since 2 is alwalys the higher one an therfore the correct answer) 
            if (listOfShuffledOptions[0] == 2):
                #if the key of the note is 2, increase currentGame.correctAnswers by one
                currentGame.correctAnswers = currentGame.correctAnswers + 1
#Cozmo API command say_text is used to make Cozmo talk in a (more) human like voice, to give feedback that the answer was correct
                robot.say_text("Sehr gut!", use_cozmo_voice=False,
                               duration_scalar=0.6).wait_for_completed()
            else:
#Cozmo API command is used to trigger an animation to visualize that an answer was incorrect
                robot.play_anim_trigger(cozmo.anim.Triggers.FrustratedByFailure).wait_for_completed()
                #increase currentGame.gameRoundMistakes by one
                currentGame.gameRoundMistakes = currentGame.gameRoundMistakes +1
                # if the current level is not one, the level is decreased and the amount of correct answers in decreased(unless it is smaller or equals 0)
                if (currentGame.correctAnswers == 0 and currentGame.gameLevel > 1):
                    currentGame.gameLevel = currentGame.gameLevel -1
                if currentGame.correctAnswers > 0:
                    currentGame.correctAnswers = currentGame.correctAnswers - 1
           
        if (currentGame.cube2Tapped):
            print("cube 2 was tapped ", listOfShuffledOptions[1])
            # set currentGame.cube2Tapped back to false
            currentGame.cube2Tapped = False
            #check if the note assosiated with cube2 has the key 2 (since 2 is alwalys the higher one an therfore the correct answer) 
            if (listOfShuffledOptions[1] == 2):
                #if the key of the note is 2, increase currentGame.correctAnswers by one
                currentGame.correctAnswers = currentGame.correctAnswers +1
#Cozmo API command say_text is used to make Cozmo talk in a (more) human like voice, to give feedback that the answer was correct
                robot.say_text("Sehr gut!", use_cozmo_voice=False,
                               duration_scalar=0.6).wait_for_completed()
            else:
#Cozmo API command is used to trigger an animation to visualize that an answer was incorrect
                robot.play_anim_trigger(cozmo.anim.Triggers.FrustratedByFailure).wait_for_completed()
                #increase currentGame.gameRoundMistakes by one
                currentGame.gameRoundMistakes = currentGame.gameRoundMistakes +1
                # if the current level is not one, the level is decreased and the amount of correct answers in decreased(unless it is smaller or equals 0)
                if (currentGame.correctAnswers == 0 and currentGame.gameLevel > 1):
                    currentGame.gameLevel = currentGame.gameLevel -1
                if currentGame.correctAnswers > 0:
                    currentGame.correctAnswers = currentGame.correctAnswers - 1

         # if currentGame.correctAnswers equals 3 the currentGame.gameLevel is increased by one and the currentGame.correctAnswers are set to 0
        if (currentGame.correctAnswers == 3):
            currentGame.correctAnswers = 0
            if currentGame.gameLevel < 3:
#Cozmo API animation plays to visualize that there is a level up
               robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabAmazed).wait_for_completed()
            currentGame.gameLevel = currentGame.gameLevel +1
        if (currentGame.gameLevel > 3):
#Cozmo API animation plays to visualize that the last level(3) is completed and the user won the game
            robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceWinSession).wait_for_completed()
            #write in darabase and set gameOn to false, to end the main game loop
            writeInDatabase(conn, currentGame, vorname)
            gameOn = False
        print("correct answers: ", currentGame.correctAnswers)
        print("Level: ", currentGame.gameLevel)

#Cozmo API command to call the methode cozmo_program 
cozmo.run_program(cozmo_program)
