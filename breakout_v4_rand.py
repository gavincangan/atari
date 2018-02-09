import gym

# Create a breakout environment
#env = gym.make('BreakoutDeterministic-v4')
env = gym.make('BreakoutDeterministic-v4')
# Reset it, returns the starting frame
frame = env.reset()
# Render
env.render()

is_done = False
count = 0
while not is_done:
  # Perform a random action, returns the new frame, reward and whether the game is over
  frame, reward, is_done, _ = env.step(env.action_space.sample())
  #print('a')
  # Render
  if not is_done:
    env.render()
    #print('b')
    #count+=1
    #print(count)
  else:
    frame = env.reset()
    env.render
    #print('c')
    is_done = False
