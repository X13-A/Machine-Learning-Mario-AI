from pygame.locals import *
import pygame
from state import State
from qTable import QTable
from utils import SMB
import copy
from settings import USE_KEYBOARD
from settings import SHOW_MINI_DISPLAY
from settings import EPSILON_START
from settings import EPSILON_SCALING
from settings import EPSILON_MIN
from settings import MAX_STUCK_TIME
from settings import SPEEDRUN_ACTIONS
from settings import ENABLE_TRAINING
from settings import BUFFER_LENGTH
from settings import STAND_STILL_PENALTY

import random
from debug import get_time_ms
from debug import ms_to_time_str

class Training():
    def __init__(self, env, ram):
        self.env = env
        self.ram = ram
        self.done = True
        self.max_fitness = 0
        self.fitness = 0
        self.state = State(self)
        self.q_table = QTable()
        self.alpha = 0.1
        self.gamma = 0.9
        self.epsilon = EPSILON_START


        self.last_state_action = (None, None)
        self.state_action_buffer = []

        self.last_x_pos = 0
        self.last_y_pos = 0
        self.stuck_time = 0
        self.just_hit_ground = False
        self.last_mario_state = "grounded"
        self.wins = 0
        self.run = 0
        self.run_start_time = get_time_ms()
        self.just_jumped = False

    def getManualAction(self):
        action = 0
        keys = pygame.key.get_pressed()
        if keys[K_RIGHT] and keys[K_SPACE] and keys[K_LSHIFT]:
            action = 4  # Move right, jump and run
        elif keys[K_RIGHT] and keys[K_SPACE]:
            action = 2  # Move right and jump
        elif keys[K_RIGHT] and keys[K_LSHIFT]: 
            action = 3 # Move right and run
        elif keys[K_RIGHT]:
            action = 1  # Move right
        elif keys[K_LEFT]:
            action = 6 # Move left
        elif keys[K_SPACE]:
            action = 5  # Jump
        return action

    def getNextAction(self,epsilon):
        if self.just_hit_ground:
            return SPEEDRUN_ACTIONS[0], -1 # Don't spam jump
        elif random.uniform(0, 1) < epsilon:
            index = random.randint(1, len(SPEEDRUN_ACTIONS)-1)
            return SPEEDRUN_ACTIONS[index], index-1 # -1 because we ignore the first "DO NOTHING" action
        else:
            # On exploite en choisissant l'action avec la valeur Q la plus élevée pour l'état donné.
            state_combination = self.q_table.Q[str(self.state.combination())]
            index = int(max(state_combination, key=state_combination.get))
            return SPEEDRUN_ACTIONS[index + 1], index # +1 because we ignore the first "DO NOTHING" action

    def reset_env(self):
        run_duration = get_time_ms() - self.run_start_time
        self.fitness = self.last_x_pos - (run_duration//200)
        self.run_start_time = get_time_ms()

        self.q_table.saveQ()
        if self.run % 100 == 0:
            self.q_table.backupQ()
        self.env.reset()

        if (self.fitness > self.max_fitness): self.max_fitness = self.fitness 
        if (self.fitness > 2800): self.wins += 1

        print(f"[Run {self.run}] Fitness: {self.fitness}/{self.max_fitness} in {ms_to_time_str(run_duration)} ({self.get_win_rate()}% win rate)")
        
        self.fitness = 0

        self.done = False
        self.run += 1

    def get_win_rate(self):
        if self.run == 0: return 0
        return (int) ((self.wins / self.run) * 100)

    def back_propagate_jump(self):
        state_action_set = {}

        for state_action in self.state_action_buffer:
            state_action_str = str(state_action)
            if not state_action_set.get(state_action_str):
                state_action_set[state_action_str] = state_action
        
        for key in state_action_set:
            state = state_action_set[key][0]
            action = state_action_set[key][1]
            self.q_table.Q[str(state)][str(action)] -= 1

    def detect_stuck(self, pos):
        if (self.last_x_pos == pos): self.stuck_time += 1
        else: self.stuck_time = 0

    def adjust_reward(self, reward, info):
        if (reward < -1): reward *= 10
        if (reward == 5): reward *= 10 #TODO: back propagate to all level when winnning
        if (reward == 0): 
            reward = STAND_STILL_PENALTY # Penalty when not moving right
            if (info["y_pos"] > self.last_y_pos): 
                reward += 1 # Little bonus when not moving but jumping
        return reward
    
    def is_done(self, done, info):
        # Workaround because done is not working
        return done or info["life"] < 2 or self.stuck_time > 60 * MAX_STUCK_TIME
        
    def fill_buffer(self, action_index):
        if self.just_jumped and self.last_state_action[0]:
            self.state_action_buffer.append(self.last_state_action)
        if self.last_mario_state == "floating":
            self.state_action_buffer.append((self.state.combination(), action_index))
        if self.just_hit_ground:
            self.state_action_buffer.clear()

        self.last_state_action = self.state.combination(), action_index

    def should_train(self, action_index):
        return not USE_KEYBOARD and ENABLE_TRAINING and action_index != -1

    def set_jump_state(self):
        mario_state = SMB.get_mario_state(self.ram)
        self.just_hit_ground = self.last_mario_state == "floating" and mario_state == "grounded"
        self.just_jumped = self.last_mario_state == "grounded" and mario_state == "floating"
        self.last_mario_state = mario_state

    def update(self):
        if self.done: self.reset_env()
        self.set_jump_state()
        # Get next action
        if USE_KEYBOARD and SHOW_MINI_DISPLAY: action = self.getManualAction()
        else: action, action_index = self.getNextAction(self.epsilon)
        self.epsilon *= EPSILON_SCALING
        if (self.epsilon < EPSILON_MIN): self.epsilon = EPSILON_MIN

        old_state = copy.copy(self.state)
        
        total_reward = 0
        
        while True :
            frame, reward, done, truncated, info = self.env.step(action)

            
            self.state.update(self.ram)
            self.detect_stuck(info["x_pos"])
            total_reward += self.adjust_reward(reward, info)

            self.last_x_pos = info["x_pos"]
            self.last_y_pos = info["y_pos"]

            self.done = self.is_done(done, info)
            
            if (old_state.combination()!=self.state.combination()) or self.done or not self.should_train() :
                break
        
        if self.should_train(action_index):
            self.fill_buffer(action_index)
            self.q_table.update(
                old_state,
                self.state,
                action_index,
                self.gamma,
                self.alpha,
                total_reward
            )
            if total_reward < STAND_STILL_PENALTY:
                self.back_propagate_jump()
