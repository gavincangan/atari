import gym
import numpy as np
# import cv2 as cv
import keras
from ring_buffer import RingBuffer


def to_grayscale(img):
    return np.mean(img, axis=2).astype(np.uint8)


def downsample(img):
    return img[::2, ::2]


def preprocess(img):
    return to_grayscale(downsample(img))


def transform_reward(reward):
    return np.sign(reward)


def get_epsilon_for_iteration(iteration):
    return 0.99


def choose_best_action(model, state):
    return 0


def action_to_onehot(action):
    action_space = (0, 1, 2, 3)
    action_onehot = np.zeros_like(action_space)
    action_onehot[action] = 1
    return action_onehot


def fit_batch(model, gamma, start_states, actions, rewards, next_states, is_terminal):
    """Do one deep Q learning iteration.

    Params:
    - model: The DQN
    - gamma: Discount factor (should be 0.99)
    - start_states: numpy array of starting states
    - actions: numpy array of one-hot encoded actions corresponding to the start states
    - rewards: numpy array of rewards corresponding to the start states and actions
    - next_states: numpy array of the resulting states corresponding to the start states and actions
    - is_terminal: numpy boolean array of whether the resulting state is terminal

    """
    # First, predict the Q values of the next states. Note how we are passing ones as the mask.
    next_Q_values = model.predict([next_states, np.ones(actions.shape)])
    # The Q values of the terminal states is 0 by definition, so override them
    next_Q_values[is_terminal] = 0
    # The Q values of each start state is the reward + gamma * the max next state Q value
    Q_values = rewards + gamma * np.max(next_Q_values, axis=1)
    # Fit the keras model. Note how we are passing the actions as the mask and multiplying
    # the targets by the actions.
    model.fit(
        [start_states, actions], actions * Q_values[:, None],
        nb_epoch=1, batch_size=len(start_states), verbose=0
    )


def atari_model(n_actions):
    # We assume a theano backend here, so the "channels" are first.
    ATARI_SHAPE = (105, 80, 4)

    # With the functional API we need to define the inputs.
    frames_input = keras.layers.Input(ATARI_SHAPE, name='frames')
    actions_input = keras.layers.Input((n_actions,), name='mask')

    # Assuming that the input frames are still encoded from 0 to 255. Transforming to [0, 1].
    normalized = keras.layers.Lambda(lambda x: x / 255.0)(frames_input)

    # "The first hidden layer convolves 16 8×8 filters with stride 4 with the input image and applies a rectifier nonlinearity."
    conv_1 = keras.layers.convolutional.Convolution2D(
        16, 8, 8, subsample=(4, 4), activation='relu'
    )(normalized)
    # "The second hidden layer convolves 32 4×4 filters with stride 2, again followed by a rectifier nonlinearity."
    conv_2 = keras.layers.convolutional.Convolution2D(
        32, 4, 4, subsample=(2, 2), activation='relu'
    )(conv_1)
    # Flattening the second convolutional layer.
    conv_flattened = keras.layers.core.Flatten()(conv_2)
    # "The final hidden layer is fully-connected and consists of 256 rectifier units."
    hidden = keras.layers.Dense(256, activation='relu')(conv_flattened)
    # "The output layer is a fully-connected linear layer with a single output for each valid action."
    output = keras.layers.Dense(n_actions)(hidden)
    # Finally, we multiply the output by the mask!
    filtered_output = keras.layers.merge([output, actions_input], mode='mul')

    model = keras.models.Model(input=[frames_input, actions_input], output=filtered_output)
    optimizer = optimizer=keras.optimizers.RMSprop(lr=0.00025, rho=0.95, epsilon=0.01)
    model.compile(optimizer, loss='mse')
    return model

def q_iteration(env, model, state, iteration, memory):
    # Choose epsilon based on the iteration
    epsilon = get_epsilon_for_iteration(iteration)

    # Choose the action
    if random.random() < epsilon:
        action = env.action_space.sample()
    else:
        action = choose_best_action(model, state)

    # Play one game iteration (note: according to the next paper, you should actually play 4 times here)
    new_frame, reward, is_done, _ = env.step(action)
    memory.add(state, action, new_frame, reward, is_done)

    # Sample and fit
    batch = memory.sample_batch(32)
    fit_batch(model, batch)


def main():

    env = gym.make('BreakoutDeterministic-v4')
    frame = env.reset()
    env.render()

    frames_per_action = 4
    num_actions = 4
    ATARI_SHAPE_PLUSONE = (105, 80, 5)
    num_games = 10

    this_states = RingBuffer(5)
    this_rewards = RingBuffer(4)

    all_prev_states = []
    all_next_states = []
    all_actions = []
    all_rewards = []
    all_isterminal = []

    # print('a')
    prev_frame = preprocess(frame)
    for this_game in range(0,num_games):
        iter_count = 0
        is_done = False
        while not is_done:
            this_action = env.action_space.sample()
            # print('b')
            this_action_onehot = action_to_onehot(this_action)
            this_states.append(prev_frame)
            for action_count in range(0,frames_per_action):
                # print('c')
                frame, reward, is_done, _ = env.step(this_action)
                this_states.append(preprocess(frame))
                this_rewards.append(transform_reward(reward))
                if not is_done:
                    env.render()
                else:
                    frame = env.reset()
                    env.render()
                    break
            prev_frame = frame
            if(iter_count>0):
                all_prev_states.append(this_states.clip_from_end(1))
                all_next_states.append(this_states.clip_from_start(1))
                all_rewards.append(this_rewards)
                all_actions.append(this_action)
                all_isterminal.append(int(is_done))
                # is_done = False
            iter_count += 1
            # input()
    np_prev_states = np.asarray(all_prev_states)
    # print('prev states: ',np.shape(np_prev_states))
    np_next_states = np.asarray(all_next_states)
    # print('next states: ',np.shape(np_next_states))
    np_rewards = np.asarray(all_rewards)
    # np_rewards = np_rewards[:-1,:]
    # print('rewards: ',np.shape(np_rewards))
    np_actions = np.asarray(all_actions)
    # np_actions = np_actions[:-1]
    # print('actions: ',np.shape(np_actions))
    np_isterminal = np.asarray(all_isterminal)
    # np_isterminal = np_isterminal[:-1]
    # print('isterminal: ',np.shape(np_isterminal))

    np_num_objects = np.size(np_isterminal)
    # print('num_objects:',np_num_objects)

    t_model = atari_model(num_actions)


if __name__=="__main__":
    main()
