import tensorflow as tf
import tensorflow.examples.tutorials.mnist.input_data as input_data
import numpy as np
import matplotlib.pyplot as plt

mnist = input_data.read_data_sets("MNIST_data/", one_hot=True)

save_path = r"G:\PycharmProjects\1028\tensorflowlianxi\save_vae_ckpt"

class EncoderNet:
    def __init__(self):
        self.in_w = tf.Variable(tf.truncated_normal(shape=[784, 100], stddev=0.1))
        self.in_b = tf.Variable(tf.zeros([100]))

        self.logvar_w = tf.Variable(tf.truncated_normal(shape=[100, 128], stddev=0.1))
        self.mean_w = tf.Variable(tf.truncated_normal(shape=[100, 128], stddev=0.1))

    def forward(self,x):
        y = tf.nn.relu(tf.matmul(x, self.in_w) + self.in_b)
        mean = tf.matmul(y, self.mean_w)
        logvar = tf.matmul(y, self.logvar_w)
        return mean, logvar


class DecoderNet:
    def __init__(self):
        self.in_w = tf.Variable(tf.truncated_normal(shape=[128, 100], stddev=0.1))
        self.in_b = tf.Variable(tf.zeros([100]))

        self.out_w = tf.Variable(tf.truncated_normal(shape=[100, 784], stddev=0.1))

    def forward(self, x):
        y = tf.nn.relu(tf.matmul(x, self.in_w) + self.in_b)
        return tf.matmul(y, self.out_w)



class Net:

    def __init__(self):
        self.x = tf.placeholder(dtype=tf.float32, shape=[None, 28 * 28])

        self.encoderNet = EncoderNet()
        self.decoderNet = DecoderNet()

        self.forward()
        self.backward()

    def forward(self):
        self.mean, self.logVar = self.encoderNet.forward(self.x)
        normal_y = tf.random_normal(shape=[128])
        self.var = tf.exp(self.logVar)
        std = tf.sqrt(self.var)
        y = normal_y * std + self.mean
        self.output = self.decoderNet.forward(y)

    def decode(self):
        normal_x = tf.random_normal(shape=[1,128])
        return self.decoderNet.forward(normal_x)


    def backward(self):
        output_loss = tf.reduce_mean((self.x-self.output)**2)
        kl_loss = tf.reduce_mean(0.5*(-self.logVar+self.mean**2+self.var-1))
        self.loss = kl_loss+output_loss

        self.opt = tf.train.AdamOptimizer().minimize(self.loss)

if __name__ == '__main__':

    net = Net()
    test_output = net.decode()
    init = tf.global_variables_initializer()

    save = tf.train.Saver()

    with tf.Session() as sess:
        sess.run(init)

        # plt.ion()
        for epoch in range(1000000):
            xs,_ = mnist.train.next_batch(100)

            _loss,_ = sess.run([net.loss,net.opt],feed_dict={net.x:xs})
            if epoch%100 == 0:
                print(_loss)
                # test_img_data = sess.run([test_output])
                # test_img = np.reshape(test_img_data,[28,28])
                # plt.imshow(test_img)
                # plt.pause(0.1)

                save.save(sess,save_path)



