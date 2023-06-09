from models.modalfusion.fuse import Fusion, TripletLoss
from tqdm import tqdm
import torch
import torch.optim as optim
import torch.nn as nn
import os

import torch
from torch.utils.tensorboard import SummaryWriter
from enrico_utils.get_embedding_data import get_embedding_dataloader

def train(device, train_loader, net, optimizer, criterion):
    train_loss = 0.0
    for i, data in tqdm(enumerate(train_loader, 0), desc="iters"):
        anchor, positive, negative = data[0], data[1], data[2]
        anchor, positive, negative = anchor.to(device), positive.to(device), negative.to(device)
        
        anchor_to_embedding = net(anchor)
        positive_to_embedding = net(positive)
        negative_to_embedding = net(negative)
        
        optimizer.zero_grad()
        loss = criterion(anchor_to_embedding, positive_to_embedding, negative_to_embedding)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()

    loss = train_loss / len(train_loader)
    return loss

def configure_trian(is_continue, net, current_best_model):
    if is_continue:
        # load current best model
        checkpoint = torch.load(current_best_model)
        net.load_state_dict(checkpoint['net'])
        start_epoch = checkpoint['epoch']
        loss = checkpoint['loss']
        print('Start training from epoch {}...' .format(start_epoch+1))
    else:
        start_epoch = 0
        loss = 10000
        print('Start training from scratch...')
    return start_epoch, loss

def operations(config: dict, net):
    writer = SummaryWriter()
    # load on gpu if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    criterion = nn.TripletMarginLoss()
    #criterion = TripletLoss()

    # load data
    dataloader = get_embedding_dataloader("enrico_corpus", config['source_data'], batch_size=config['batch_size'])
    # initialize net
    net.to(device)
    
    print("Training " + config["net"] + "...")

    # use adam optimizer
    optimizer = optim.Adam(net.parameters(), lr=config['learning_rate'], betas=(0.9, 0.999), eps=1e-08, weight_decay=config['weight_decay'])

    start_epoch, bench_loss = configure_trian(config['is_continue'], net, config['continue_on'])
    
    for epoch in range(start_epoch, start_epoch + config['num_epochs']):
        loss = train(device, dataloader, net, optimizer, criterion)
        writer.add_scalar("Loss/train", loss, epoch)
        writer.flush()

        print('epoch:{}, loss:{}'.format(epoch + 1, loss * 100))
        print("------------------------------------")
        # only store the models that imporve on validation and drop in loss
        if loss < bench_loss or epoch % 10 == 0 :
            bench_loss = loss

            print('Saving model...')
            state = {
                'net': net.state_dict(),
                'epoch': epoch+1,
                'loss': loss,
            }

            if not os.path.isdir(config['weights']):
                os.mkdir(config['weights'])
            torch.save(state, config['weights'] + 'fuse_epoch_{}.ckpt'.format(epoch+1))

    print('Finished Training!')


def fusemodel():
    fuse_config = {
        'net': 'fusemodel',
        'batch_size': 64,
        'num_epochs': 300,
        'learning_rate': 0.001,
        'weight_decay': 1e-08,
        'is_continue': False,
        # 'source_data': 'enrico_expanded_embedding.pkl',
        'source_data': 'enrico_expanded_embedding_nlp.pkl',
        'weights': './weights/fusemodel_no_cv/',
        'continue_on': './weights/fusemodel/fuse_no_cv_epoch_1.ckpt',
    }
    net = Fusion()
    operations(fuse_config, net)

if __name__ == '__main__':
    fusemodel()
    
    
    