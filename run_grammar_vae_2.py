import h5py
import numpy as np
import os, inspect
import torch.utils.data
import torch.optim as optim
from torch.autograd import Variable
from torch.optim import lr_scheduler

from grammar_variational_autoencoder.models.grammar_helper import grammar_eq, grammar_zinc
from models.model_grammar_pytorch import GrammarVariationalAutoEncoder, VAELoss
from basic_pytorch.fit import fit
from basic_pytorch.data_utils.data_sources import DatasetFromHDF5, train_valid_loaders
from basic_pytorch.gpu_utils import to_gpu, use_gpu

EPOCHS = 1
BATCH_SIZE = 200

# TODO: get those from the correct GrammarModel instance?
molecules = True
if molecules:
    grammar = grammar_zinc
    data_path = 'data/zinc_grammar_dataset.h5'
    max_seq_length = 277
else:
    grammar = grammar_eq
    data_path = 'data/eq2_grammar_dataset.h5'
    max_seq_length = 15

model_args = {'z_size': 56,
              'hidden_n': 200,
              'feature_len': len(grammar.GCFG.productions()),
              'max_seq_length': max_seq_length,
              'encoder_kernel_sizes': (2, 3, 4)}

print('loading data...')

# def kfold_loader(k, s, e=None):
#     if not e:
#         e = k
#     with h5py.File(data_path, 'r') as h5f:
#         result = np.concatenate([h5f['data'][i::k] for i in range(s, e)])
#         return torch.FloatTensor(result)
# print('done!')


model = GrammarVariationalAutoEncoder(**model_args)
optimizer = optim.Adam(model.parameters(), lr=2e-3)

class DuplicateIter:
    def __init__(self, iterable):
        self.iterable = iterable

    def __iter__(self):
        def gen():
            iter = self.iterable.__iter__()
            while True:
                # TODO: cast to float earlier?
                x = Variable(to_gpu(next(iter).float()))
                yield (x,x)
        return gen()


train_loader, valid_loader = train_valid_loaders(DatasetFromHDF5(data_path,'data'),
                                                 valid_fraction=0.1,
                                                 batch_size=BATCH_SIZE,
                                                 pin_memory=use_gpu)
# train_loader = torch.utils.data.DataLoader(kfold_loader(10, 1),
#                                           batch_size=BATCH_SIZE,
#                                           shuffle=False)
# valid_loader = torch.utils.data.DataLoader(kfold_loader(10, 0, 1),
#                                   batch_size=BATCH_SIZE,
#                                   shuffle=False)

train_gen = DuplicateIter(train_loader)
valid_gen = DuplicateIter(valid_loader)

scheduler = lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.5)

loss_obj = VAELoss(grammar)
def loss_fn(model_out, data):
    output, mu, log_var = model_out
    return loss_obj(data, mu, log_var, output)

my_location = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
save_path=my_location + '/pretrained/test.mdl'

fit(train_gen=train_gen,
    valid_gen=valid_gen,
    model=model,
    optimizer=optimizer,
    scheduler=scheduler,
    epochs=EPOCHS,
    loss_fn=loss_fn,
    save_path=save_path,
    ignore_initial=-1)

# test the Load method
model2 = GrammarVariationalAutoEncoder(**model_args)
model2.load(save_path)
# TODO: use


# if batch_idx == 0:
#     print('batch size', batch_size)
# if batch_idx % 40 == 0:
#     print('training loss: {:.4f}'.format(loss_value[0] / batch_size))

# TODO: integrate Visdom
# self.dashboard.append('training_loss', 'line',
#                                   X=np.array([self.train_step]),
#                                   Y=loss_value / batch_size)


# class Session():
#     def __init__(self, model, train_step_init=0, lr=1e-3, is_cuda=False):
#         self.train_step = train_step_init
#         self.model = model
#         self.optimizer = optim.Adam(model.parameters(), lr=lr)
#         self.loss_fn = VAELoss()
#         self.dashboard = Dashboard('Grammar-Variational-Autoencoder-experiment')
#
#     def train(self, loader, epoch_number):
#         # built-in method for the nn.module, sets a training flag.
#         self.model.train()
#         for batch_idx, data in enumerate(loader):
#             # have to cast data to FloatTensor. DoubleTensor errors with Conv1D
#             data = Variable(data)
#             # do not use CUDA atm
#             self.optimizer.zero_grad()
#             recon_batch, mu, log_var = self.model(data)
#             loss = self.loss_fn(data, mu, log_var, recon_batch)
#             loss.backward()
#             self.optimizer.step()
#             self.train_step += 1
#
#             loss_value = loss.data.numpy()
#             batch_size = len(data)
#
#
#
#
#         return losses
#
#     def test(self, loader):
#         # nn.Module method, sets the training flag to False
#         self.model.eval()
#         test_loss = 0
#         for batch_idx, data in enumerate(loader):
#             data = Variable(data, volatile=True)
#             # do not use CUDA atm
#             recon_batch, mu, log_var = self.model(data)
#             test_loss += self.loss_fn(data, mu, log_var, recon_batch).data[0]
#
#         test_loss /= len(test_loader.dataset)
#         print('testset length', len(test_loader.dataset))
#         print('====> Test set loss: {:.4f}'.format(test_loss))
