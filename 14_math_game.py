#!/usr/bin/env python3



import asyncio
from logging import Handler
import time
import sqlite3
from sqlite3 import Error
from datetime import datetime

import cozmo
import random
import array as arr
import sys
from cozmo.event import wait_for_first
from cozmo.objects import LightCube1Id, LightCube2Id
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cannot import from PIL. Do `pip3 install --user Pillow` to install")

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
            INSERT INTO mathGame 
                    VALUES (?,?,?,?,?)
            """, 
            (vorname, currentGame.gameStart, currentGame.gameEnd, currentGame.gameRoundMistakes, currentGame.gameLevel)
            )
    conn.commit()
    conn.close()

#######Text on Face#####
# drwas the image/math problem on Cozmos face, while text_to_draw is the problem, x and y are the position the text will start at
# returns text_image, the image to show in Cozmos OLED screen (his face)
def make_text_image(text_to_draw, x, y, font=None):
    '''Make a PIL.Image with the given text printed on it

    Args:
        text_to_draw (string): the text to draw to the image
        x (int): x pixel location
        y (int): y pixel location
        font (PIL.ImageFont): the font to use

    Returns:
        :class:(`PIL.Image.Image`): a PIL image with the text drawn on it
    '''

    # make a blank image for the text, initialized to opaque black
    text_image = Image.new('RGBA', cozmo.oled_face.dimensions(), (0, 0, 0, 255))

    # get a drawing context
    dc = ImageDraw.Draw(text_image)

    # draw the text
    dc.text((x, y), text_to_draw, fill=(255, 255, 255, 255), font=font)

    return text_image

# splits a string(a math problem) into it's elements, to extract the numeric values that are to be calculated with each other
# returns an array of both digits and the result of their addition, the given string contains two numbers
# throws a valueError if string does not contain digits
# returns none if exception is thrown
def split_banana(string):
    split_time_args = []
    for element in range(0, len(string)):
        if (string[element].isnumeric()):
            split_time_args.append(string[element])

    if len(split_time_args) >= 2:
        try:
            firstInt = convert_problem_to_int(split_time_args[0])
            secondInt = convert_problem_to_int(split_time_args[1])
            result = firstInt + secondInt
            bufferArray = arr.array('b', [firstInt, secondInt, result])            
            return bufferArray
        except ValueError as e:
            print("ValueError %s" % e)

    return None

# helper mathode for  split_banana, to check if a value is an int and not negative   
# throws ValueError if in_value is negative or not an int
#returns in_value casted to an int
def convert_problem_to_int(in_value):
    '''Convert in_value to an int and ensure it is in the valid range for that time unit

    (e.g. 0..23 for hours)'''


    try:
        int_val = int(in_value)
    except ValueError:
        raise ValueError("%s value '%s' is not an int" % (in_value))

    if int_val < 0:
        raise ValueError("%s value %s is negative" % (int_val))


    return int_val


# main program, that's where the magic happens
# calls split_banana (which calls convert_problem_to_int), make_text_image, writeInDatabase, create_table, create_connection
#has a class GameStats and will create an instance of it called currentGame
def cozmo_program(robot: cozmo.robot.Robot):
    #DATABASE STUFF
    #where the database shall be located
    database = "C:/Users/Marnick/Documents/Cozmo/cozmo_sdk_examples_1.4.10/tutorials/01_basics/CozmoDatabase.db"
    
    sql_create_projects_table = """
    CREATE TABLE IF NOT EXISTS mathGame (
    vorname VARCHAR(20), 
    gameStart DATE,
    gameEnd DATE,
    gameRoundMistakes INTEGER,
    reachedLevel INTEGER
    );"""

    # create a database connection
    conn = create_connection(database)
    # create table
    if conn is not None:
        # create mathGame table
        create_table(conn, sql_create_projects_table)

    else:
        print("Error! cannot create the database connection.")

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
# Cozmo API command, start turning towards the face
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
    # gameLevel: current level, correctAnswers: correct answers for this level while wrong ansers decrease the correct answers
    #gameStart: when this game started
    #gameEnd: when the game is over
    #problem1, problem2, problem3 and problem4 store previous problems on the current level that were answered correctly
    #result:  firstInt + secondInt, resultInput: user input (number of taps on cube)  firstInt: frist digit of the math problem, secondInt: second digit of the math problem
    class GameStats(object):
        gameLevel = 1
        correctAnswers = 0
        gameStart = datetime.now()
        gameEnd = datetime.now()
        gameRoundMistakes = 0
        problem1 = None
        problem2 = None
        problem3 = None
        problem4 = None
        result = 0
        resultInput = 0
        firstInt = 0
        secondInt = 0
        # The class "constructor" - It's actually an initializer 
        def __init__(self, gameLevel, correctAnswers, gameStart):
            self.gameLevel = gameLevel
            self.correctAnswers = correctAnswers
            self.gameStart = gameStart
            self.gameEnd = datetime.now()
            self.gameRoundMistakes = 0
            self.problem1 = ""
            self.problem2 = ""
            self.problem3 = ""
            self.problem4 = ""
            self.result = 0
            self.resultInput = 0
            self.firstInt = 0
            self.secondInt = 0


    t = datetime.now()
    # methode to make an instance of the gameStats class
    def make_gameStats(gameLevel, correctAnswers, t):
        currentGame = GameStats(gameLevel, correctAnswers, t)
        return currentGame
    
    # currentGame: instance of the gameStats class with the current time as GameStart time, 0 mistakes and Level one (since that's where we start)
    currentGame = make_gameStats(1, 0, t)


    # list of math problems, Level 1: biggest sum is 3, Level 2: biggest possible sum is 5, Level 6: biggest possible sum is 7
    allProblemsLevel1List = ["2 + 1 = ?", 
                "1 + 1 = ?", "1 + 2 = ?"]
    allProblemsLevel2List = ["2 + 2 = ?", 
                "3 + 1 = ?", "1 + 3 = ?", "3 + 2 = ?", 
                "2 + 3 = ?", "1 + 4 = ?", "4 + 1 = ?"]
    allProblemsLevel3List = ["4 + 2 = ?", 
                "2 + 4 = ?", "4 + 3 = ?", "3 + 4 = ?", 
                "5 + 2 = ?", "2 + 5 = ?", "6 + 1 = ?", "1 + 6 = ?"]

# get a font - location depends on OS so try a couple of options
# failing that the default of None will just use a default font
    _clock_font = None
    try:
        _clock_font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        try:
            _clock_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 20)
        except IOError:
            pass


    #gameOn: boolean to flag weather or not to do the main game loop
    gameOn = True
    #inputEnd: flag to mark the end of user input
    inputEnd = False
#Cozmo API commands to initialise a light cube and set it's color to green
    cube2 = robot.world.get_light_cube(LightCube1Id)
    cube2.set_lights(cozmo.lights.green_light)
#Cozmo API command to let Cozmo say text in a (more) human voice
    robot.say_text("Willkommen zum kleinen Mathespiel! Bitte benutze den leuchtenden Würfel!", use_cozmo_voice=False,
                   duration_scalar=0.6).wait_for_completed()
#Cozmo API command to turn the light of the light off
    cube2.set_lights(cozmo.lights.off_light)

#########################################################MAIN GAME LOOP STARTS HERE########################################################
    while gameOn:

# depending on the level a random problem of the list of problems (for the level) is picked
# the secon note is closer if the level is higher
        if currentGame.gameLevel == 1:
            # random_problem is picked randomly amog the 3 possible problems
            random_problem = random.randint(0, 2)
            problem = allProblemsLevel1List[random_problem]
            # if the picked prblem was alredy answered correctly before, pick another problem
            while problem == currentGame.problem1:
                random_problem = random.randint(0, 2)
                problem = allProblemsLevel1List[random_problem]
            print(problem)
#Cozmo API command to show text on Cozmos face
            face_image = make_text_image(problem, 8, 6, _clock_font)
            oled_face_data = cozmo.oled_face.convert_image_to_screen_data(face_image)
#Cozmo API command to read text in a (more) human like voice
            robot.say_text(problem, use_cozmo_voice=False,
                           duration_scalar=0.6).wait_for_completed()
# display for 30 second
            action1 = robot.display_oled_face_image(oled_face_data, 30000, in_parallel=True)
            
            
        if currentGame.gameLevel == 2:
            random_problem = random.randint(0, 6)
            problem = allProblemsLevel2List[random_problem]
            while problem == currentGame.problem1 or problem == currentGame.problem2:
                random_problem = random.randint(0, 6)
                problem = allProblemsLevel2List[random_problem]
            print(problem)
            face_image = make_text_image(problem, 8, 6, _clock_font)
#Cozmo API commands to show text in his face and to let him read it in a (more) human like voice
            oled_face_data = cozmo.oled_face.convert_image_to_screen_data(face_image)
            robot.say_text(problem, use_cozmo_voice=False,
                           duration_scalar=0.6).wait_for_completed()
# display for 30 second
            action1 = robot.display_oled_face_image(oled_face_data, 30000, in_parallel=True)
        if currentGame.gameLevel == 3:
            random_problem = random.randint(0, 7)
            problem = allProblemsLevel3List[random_problem]
            while problem == currentGame.problem1 or problem == currentGame.problem2 or problem == currentGame.problem3:
                random_problem = random.randint(0, 7)
                problem = allProblemsLevel3List[random_problem]
            print(problem)
            face_image = make_text_image(problem, 8, 6, _clock_font)
#Cozmo API commands to show text in his face and to let him read it in a (more) human like voice
            oled_face_data = cozmo.oled_face.convert_image_to_screen_data(face_image)
            robot.say_text(problem, use_cozmo_voice=False,
                           duration_scalar=0.6).wait_for_completed()
# display for 30 second
            action1 = robot.display_oled_face_image(oled_face_data, 30000, in_parallel=True)


#Cozmo API objects used in a list
        note1 = [cozmo.song.SongNote(cozmo.song.NoteTypes.G2, cozmo.song.NoteDurations.Quarter)]
# Cozmo API command to inicialize the cube
        cube1 = robot.world.get_light_cube(LightCube1Id)  # looks like a paperclip


    # if tapped turn on light of cube and play note, then turn cube light off
    #Just in case the events might be needed later eventX is stored

        while inputEnd == False:
            
            try:
#Cozmo API command, wait for cube1 to be tapped, wait for 5 seconds
                eventX = cube1.wait_for(cozmo.objects.EvtObjectTapped, timeout=5)
            #try:
            #    cube1.wait_for_first(cozmo.objects.EvtObjectTapped, timeout=30)
            #except:
            #    writeInDatabase(conn, currentGame, vorname)
            #    exit()
# Cozmo API commands, used to create input feedback, when cube is tapped, the cube lights up (green) and a sound is audible
                if cube1 is not None and inputEnd != True:
                    cube1.set_lights(cozmo.lights.green_light)
                    action2 = robot.play_song(note1, loop_count=1, in_parallel=True)
                    action2.wait_for_completed()
                    cube1.set_lights_off()
#Cozmo API command, show the math problem paralel to the cube feedback
                    action1 = robot.display_oled_face_image(oled_face_data, 30000, in_parallel=True)
                    # increase currentGame.resultInput by one for every tap
                    currentGame.resultInput = currentGame.resultInput + 1
                    print("Input: ", currentGame.resultInput)
                if cube1 is None:
# Cozmo API logger warning if something is wrong with the cube
                    cozmo.logger.warning("Cozmo is not connected to a LightCube1Id cube - check the battery.")
            # when for 5 seconds after the last tap, no additional tap is detected, inputEnd is set to true
            except:
                print("Input end: ", currentGame.resultInput)
                inputEnd = True
                
      

       

        #Game logic
        # if the input is complete, 
        if inputEnd == True:
            #call split_banana on the currently displayed math problem, store all digits in the array bufferArray
            bufferArray = split_banana(problem)
            print(bufferArray)
            currentGame.firstInt = bufferArray[0]
            currentGame.secondInt = bufferArray[1]
            currentGame.result = bufferArray[2]
#Cozmo API commands to aboart all actions (stop showing the math problem on his face), wait for this abort
            robot.abort_all_actions()
            robot.wait_for_all_actions_completed()
            print("result: ", currentGame.result, "Input: ", currentGame.resultInput)
            # set inputEnd to false for the next round
            inputEnd = False

        # if the detected taps and the result of the problem are the same
        if (currentGame.resultInput == currentGame.result):
            # set of phrases to praise the player for a corerct answer
            wintext = ["Das war super! ", "Toll gemacht! ", "Sehr gut! "]
            #currentGame.correctAnswers is increased by one
            currentGame.correctAnswers = currentGame.correctAnswers + 1
#Cozmo API command say_text is used to make Cozmo talk in a (more) human like voice, to give feedback that the answer was correct
            robot.say_text(random.choice(wintext), use_cozmo_voice=False,
                           duration_scalar=0.6).wait_for_completed()
            # depending on the level, store solved problems
            if (currentGame.gameLevel == 1):
                if currentGame.problem1 != 0 and currentGame.problem2 == 0:
                    currentGame.problem2 = problem
                if currentGame.problem1 == 0:
                    currentGame.problem1 = problem
            if (currentGame.gameLevel == 2):
                if currentGame.problem1 != 0 and currentGame.problem2 != 0 and currentGame.problem3 == 0:
                    currentGame.problem3 = problem
                if currentGame.problem1 != 0 and currentGame.problem2 == 0:
                    currentGame.problem2 = problem
                if currentGame.problem1 == 0:
                    currentGame.problem1 = problem
            if (currentGame.gameLevel == 3):
                if currentGame.problem1 != 0 and currentGame.problem2 != 0 and currentGame.problem3 != 0 and currentGame.problem4 == 0:
                    currentGame.problem4 = problem
                if currentGame.problem1 != 0 and currentGame.problem2 != 0 and currentGame.problem3 == 0:
                    currentGame.problem3 = problem
                if currentGame.problem1 != 0 and currentGame.problem2 == 0:
                    currentGame.problem2 = problem
                if currentGame.problem1 == 0:
                    currentGame.problem1 = problem
        else:
#Cozmo API command to play animation to visualise a wrong answer
            robot.play_anim_trigger(cozmo.anim.Triggers.FrustratedByFailure).wait_for_completed()
            # currentGame.gameRoundMistakes is incresed by one
            currentGame.gameRoundMistakes = currentGame.gameRoundMistakes +1
            # if the current level is not one, the level is decreased and the amount of correct answers in decreased(unless it is smaller than, or equals 0)
            if (currentGame.correctAnswers == 0 and currentGame.gameLevel > 1):
                currentGame.gameLevel = currentGame.gameLevel -1
            if currentGame.correctAnswers > 0:
                currentGame.correctAnswers = currentGame.correctAnswers - 1
            currentGame.resultInput = 0
         
        # set currentGame.resultInput to 0 for the next round
        currentGame.resultInput = 0
        # depending on the level, decide whether or not to increase the currentGame.gameLevel 
        if (currentGame.gameLevel == 1):          
            if currentGame.correctAnswers == 2:
                currentGame.correctAnswers = 0
                if currentGame.gameLevel < 3:
# Cozmo API command to play animation to visualise that the user made it to a level up
                    robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabAmazed).wait_for_completed()
                currentGame.gameLevel = currentGame.gameLevel +1
                # set problems to zero for the next level
                currentGame.problem1 = 0 
                currentGame.problem2 = 0

        # depending on the level, decide whether or not to increase the currentGame.gameLevel
        if (currentGame.gameLevel == 3):
            if currentGame.correctAnswers == 4:
                currentGame.correctAnswers = 0
                if currentGame.gameLevel < 4:
# Cozmo API command to play animation to visualise that the user made it to a level up
                    robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabAmazed).wait_for_completed()
                currentGame.gameLevel = currentGame.gameLevel +1
                # set problems to zero for the next level
                currentGame.problem1 = 0 
                currentGame.problem2 = 0
                currentGame.problem3 = 0
                currentGame.problem4 = 0

        # depending on the level, decide whether or not to increase the currentGame.gameLevel
        if (currentGame.gameLevel == 2):
            if currentGame.correctAnswers == 3:
                currentGame.correctAnswers = 0
                if currentGame.gameLevel < 3:
# Cozmo API command to play animation to visualise that the user made it to a level up
                    robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabAmazed).wait_for_completed()
                currentGame.gameLevel = currentGame.gameLevel +1
                # set problems to zero for the next level
                currentGame.problem1 = 0 
                currentGame.problem2 = 0
                currentGame.problem3 = 0
    
        # depending on the level, decide whether or not to increase the currentGame.gameLevel
        if (currentGame.gameLevel > 3):
# Cozmo API command to play animation to visualise that the user made it to a level up
            robot.play_anim_trigger(cozmo.anim.Triggers.CubePounceWinSession).wait_for_completed()
            # call writeInDatabase and set gameOn to false to exit the main game loop
            writeInDatabase(conn, currentGame, vorname)
            gameOn = False
            break
        
        print("correct answers: ", currentGame.correctAnswers)
        print("Level: ", currentGame.gameLevel)

#Cozmo API command to call the methode cozmo_program 
cozmo.run_program(cozmo_program)
