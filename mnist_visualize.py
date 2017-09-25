# encoding: utf-8

import os
import torch
import random
import argparse
from PIL import Image, ImageDraw
from mnist_model import STNClsNet
from grid_sample import grid_sample
from torch.autograd import Variable
from torchvision import datasets, transforms

parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
parser.add_argument('--batch-size', type=int, default=64, metavar='N')
parser.add_argument('--no-cuda', action='store_true', default=False)
parser.add_argument('--checkpoint', required = True)
parser.add_argument('--angle', type = int, default=60)
args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()

test_loader = torch.utils.data.DataLoader(
    datasets.MNIST(
        'mnist_data',
        train = False,
        transform = transforms.Compose([
            transforms.Lambda(lambda image: image.rotate(random.random() * args.angle * 2 - args.angle)),
            transforms.ToTensor(),
        ]),
    ),
    batch_size = args.batch_size,
    shuffle = True,
    num_workers = 4,
    pin_memory = True if args.cuda else False,
)

model = STNClsNet()
model.load_state_dict(torch.load(args.checkpoint))

if not os.path.isdir('image'):
    os.makedirs('image')

for batch_idx, (source_data, target) in enumerate(test_loader):
    print(batch_idx)
    if args.cuda:
        source_data = source_data.cuda()
    batch_size = source_data.size(0)
    source_data = Variable(source_data, volatile = True)
    source_control_points = model.loc_net(source_data)
    source_coordinate = model.tps(source_control_points)
    grid = source_coordinate.view(batch_size, 28, 28, 2)
    target_data = grid_sample(source_data, grid)

    concat_data = torch.cat([source_data, target_data], 3)
    concat_images = (concat_data.data * 255).cpu().numpy().astype('uint8')
    for i in range(batch_size):
        image = Image.fromarray(concat_images[i, 0]).convert('RGB')
        image = image.resize((256, 128))
        source_points = source_control_points.data[i]
        draw = ImageDraw.Draw(image)
        for x, y in source_points:
            x = (x + 1) / 2 * 128
            y = (y + 1) / 2 * 128
            draw.rectangle([x - 1, y - 1, x + 1, y + 1], fill = (255, 0, 0))
        image.save('image/%04d.jpg' % (batch_idx * args.batch_size + i))
