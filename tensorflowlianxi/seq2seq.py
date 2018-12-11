#识别验证码

import tensorflow as tf
import os
import matplotlib.image as imgplt
import matplotlib.pyplot as plt
import numpy as np
import PIL.Image as pimg
import PIL.ImageDraw as pdraw
import PIL.ImageFont as Font

image_path = r"G:\PycharmProjects\1028\tensorflowlianxi\code"
font_path = r"G:\PycharmProjects\1028\tensorflowlianxi\arial.ttf"
#模型保存路径
save_path = r"G:\PycharmProjects\1028\tensorflowlianxi\save_ckpt"
#批次
batch_size = 100

#rnn编码
class EncoderNet:
    def __init__(self):
        # NHWC(100*60*120*3)-NWHC(100*120*60*3)-NW*HC=NV,V=60*3
        # 60*120的图片，100个批次拼接，120为步长，60为数据  现在就变成了N（100*120）* V（60*3） RGB三通道
        self.w1 = tf.Variable(tf.truncated_normal(shape=[60*3,128]))
        self.b1 = tf.Variable(tf.zeros([128]))

    def forward(self,x):
        #变量名只能在EncoderNet网络范围里使用
        with tf.name_scope("EncoderNet") as scope:
            #NHWC-->NWHC,矩阵转置
            y = tf.transpose(x,[0,2,1,3])

            #重置形状,NHWC(10*60*120*3)-NWHC(10*120*60*3)-NW*HC=NV,N=10*120,V=60*3
            y = tf.reshape(y,[batch_size*120,60*3])

            #[10*120,60*3]*[60*3,128]
            y = tf.nn.relu(tf.matmul(y,self.w1) + self.b1)
            #NV-NSC:[10*120,128]-[10,120,128]
            y = tf.reshape(y,[batch_size,120,128])

            cell = tf.nn.rnn_cell.BasicLSTMCell(128)
            init_state = cell.zero_state(batch_size,dtype=tf.float32)
            encoder_outputs,encoder_final_state = tf.nn.dynamic_rnn(cell,y,initial_state=init_state,time_major=False,scope=scope)

            #NSV-SNV[-1]:[100,120,128]-[120,100,128][-1]=[100,128]
            y = tf.transpose(encoder_outputs,[1,0,2])[-1]
            return y #[100,128]

#rnn解码
class DecoderNet:
    def __init__(self):
        #10分类问题
        self.w1 = tf.Variable(tf.truncated_normal(shape=[128,10]))
        self.b1 = tf.Variable(tf.zeros([10]))

    def forward(self,x):
        #变量名只能在DecoderNet网络范围里使用
        with tf.name_scope("DecoderNet") as scope:
            #扩维度，在第一维前面扩展一维：[10,128]：十分类对应128个记忆细胞 -->[10,1,128]
            y = tf.expand_dims(x,axis=1)

            # 广播第一维,[10,1,128]*[1,4,1]=[10,4,128]
            y = tf.tile(y,[1,4,1])

            cell = tf.nn.rnn_cell.BasicLSTMCell(128) #128个记忆细胞
            init_state = cell.zero_state(batch_size,dtype=tf.float32)
            decoder_outputs,decoder_final_state = tf.nn.dynamic_rnn(cell,y,initial_state=init_state,time_major=False,scope=scope)

            # 形状重置，NSV-NV:[10,4,128]-[10*4,128]
            y = tf.reshape(decoder_outputs,[batch_size*4,128])
            # [10*4,128]*[128*10]
            self.y1 = tf.matmul(y,self.w1) + self.b1

            # NV-NSV:[10*4,10]-[10,4,10] 没激活数据
            self.y1 = tf.reshape(self.y1,[-1,4,10])

            #激活后的数据
            y = tf.nn.softmax(self.y1)
            return y #[10,4,10]

#全连接fcn
class Net:
    def __init__(self):
        #输入NHWC
        self.x = tf.placeholder(dtype=tf.float32,shape=[batch_size,60,120,3])
        #输出NSV ，十分类 四个数字步长
        self.y = tf.placeholder(dtype=tf.float32,shape=[batch_size,4,10])
        #实例化编码网络
        self.encoderNet = EncoderNet()
        #实例化解码网络
        self.decoderNet = DecoderNet()

    def forward(self):
        # 调用编码网络的前向运算函数，传入参数（归一化后的图像），得到最终的向量y
        y = self.encoderNet.forward(self.x)

        #调用解码网络的前向运算函数，传入参数（编码后的向量y），得到最终结果
        self.output = self.decoderNet.forward(y)

    def backward(self):
        self.loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=self.decoderNet.y1,labels=self.y))
        self.opt = tf.train.AdamOptimizer().minimize(self.loss)

#采样类
class Sampling:
    def __init__(self):
        self.image_dataset = []
        #遍历列表系统里的每一个文件
        for filename in os.listdir(image_path):
            #从每个文件读取每个图像数据，归一化处理
            x = imgplt.imread(os.path.join(image_path,filename)) / 255 - 0.5
            #用 . 将数据和文件名分开，xxxx . jpg, ys表示文件名
            ys = filename.split(".")
            #取出第0轴的数据，进行one_hot处理
            y = self.__one_hot(ys[0])
            #处理完后再拼接起来
            self.image_dataset.append([x,y])

    def __one_hot(self,x):
        #生成一个4行10列的0矩阵
        z = np.zeros(shape=(4,10))
        for i in range(4):
            #取出第i行的值x的下标index，转成int格式
            index= int(x[i])
            #遍历矩阵，取出每一行的下标
            z[i][index] += 1
        return z

    #获得图片批次方法
    def image_get_batch(self,size):
        xs = []
        ys = []
        for _ in range(size):
            #定义下标为 随机int型，从0到数据集的长度
            index = np.random.randint(0,len(self.image_dataset))
            #将数据集的第[0]维的下标连起来
            xs.append(self.image_dataset[index][0])
            #将数据集的第[1]维的下标连起来
            ys.append(self.image_dataset[index][1])
        return xs,ys

if __name__ == '__main__':
    sample = Sampling()

    net = Net()
    net.forward()
    net.backward()
    init = tf.global_variables_initializer()

    plt.ion()
    a = []
    b = []
    save = tf.train.Saver()

    with tf.Session() as sess:
        # sess.run(init)
 
        #读取模型
        save.restore(sess,save_path=save_path)

        for i in range(1000000):
            xs,ys = sample.image_get_batch(batch_size)
            loss,_ = sess.run([net.loss,net.opt],feed_dict={net.x:xs,net.y:ys})

            if i % 100 == 0:
                xss,yss = sample.image_get_batch(batch_size)
                output = sess.run(net.output,feed_dict={net.x:xss,net.y:yss})
                print("shape:",np.shape(output))
                print("loss:",loss)

                output = np.argmax(output[0],axis=1)
                label = np.argmax(yss[0],axis=1)
                print("accuracy:",np.mean(np.array(output==label,dtype=np.float32)))
                print("output:",output)
                print("label:",label)

                # #损失图
                # a.append(i)
                # b.append(loss)
                # plt.clf()
                # plt.plot(a,b)
                # plt.pause(0.01)

                #标签和输出图片对比
                img = (xss[0]+0.5) * 255
                image = pimg.fromarray(np.uint8(img))
                imgdraw = pdraw.ImageDraw(image)
                font = Font.truetype(font_path,size=20)
                imgdraw.text(xy=(0, 0), text=str(output), fill="red", font=font)
                image.show()

                # save.save(sess,save_path)
