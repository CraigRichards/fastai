# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_data.core.ipynb (unless otherwise specified).

__all__ = ['show_batch', 'show_results', 'TfmdDL', 'DataLoaders', 'FilteredBase', 'TfmdLists', 'decode_at', 'show_at',
           'Datasets', 'test_set']

# Cell
from ..torch_basics import *
from .load import *

# Cell
@typedispatch
def show_batch(
    x, # Input(s) in the batch
    y, # Target(s) in the batch
    samples, # List of (`x`, `y`) pairs of length `max_n`
    ctxs=None, # List of `ctx` objects to show data. Could be a matplotlib axis, DataFrame, etc.
    max_n=9, # Maximum number of `samples` to show
    **kwargs
):
    "Show `max_n` input(s) and target(s) from the batch."
    if ctxs is None: ctxs = Inf.nones
    if hasattr(samples[0], 'show'):
        ctxs = [s.show(ctx=c, **kwargs) for s,c,_ in zip(samples,ctxs,range(max_n))]
    else:
        for i in range_of(samples[0]):
            ctxs = [b.show(ctx=c, **kwargs) for b,c,_ in zip(samples.itemgot(i),ctxs,range(max_n))]
    return ctxs

# Cell
@typedispatch
def show_results(
    x, # Input(s) in the batch
    y, # Target(s) in the batch
    samples, # List of (`x`, `y`) pairs of length `max_n`
    outs, # List of predicted output(s) from the model
    ctxs=None, # List of `ctx` objects to show data. Could be a matplotlib axis, DataFrame, etc.
    max_n=9, # Maximum number of `samples` to show
    **kwargs
):
    "Show `max_n` results with input(s), target(s) and prediction(s)."
    if ctxs is None: ctxs = Inf.nones
    for i in range(len(samples[0])):
        ctxs = [b.show(ctx=c, **kwargs) for b,c,_ in zip(samples.itemgot(i),ctxs,range(max_n))]
    for i in range(len(outs[0])):
        ctxs = [b.show(ctx=c, **kwargs) for b,c,_ in zip(outs.itemgot(i),ctxs,range(max_n))]
    return ctxs

# Cell
#nbdev_comment _all_ = ["show_batch", "show_results"]

# Cell
_batch_tfms = ('after_item','before_batch','after_batch')

# Cell
@delegates()
class TfmdDL(DataLoader):
    "Transformed `DataLoader`"
    def __init__(self,
        dataset, # Map- or iterable-style dataset from which to load the data
        bs:int=64, # Size of batch
        shuffle:bool=False, # Whether to shuffle data
        num_workers:int=None, # Number of CPU cores to use in parallel (default: All available up to 16)
        verbose:bool=False, # Whether to print verbose logs
        do_setup:bool=True, # Whether to run `setup()` for batch transform(s)
        **kwargs
    ):
        if num_workers is None: num_workers = min(16, defaults.cpus)
        for nm in _batch_tfms: kwargs[nm] = Pipeline(kwargs.get(nm,None))
        super().__init__(dataset, bs=bs, shuffle=shuffle, num_workers=num_workers, **kwargs)
        if do_setup:
            for nm in _batch_tfms:
                pv(f"Setting up {nm}: {kwargs[nm]}", verbose)
                kwargs[nm].setup(self)

    def _one_pass(self):
        b = self.do_batch([self.do_item(None)])
        if self.device is not None: b = to_device(b, self.device)
        its = self.after_batch(b)
        self._n_inp = 1 if not isinstance(its, (list,tuple)) or len(its)==1 else len(its)-1
        self._types = explode_types(its)

    def _retain_dl(self,b):
        if not getattr(self, '_types', None): self._one_pass()
        return retain_types(b, typs=self._types)

    @delegates(DataLoader.new)
    def new(self,
        dataset=None, # Map- or iterable-style dataset from which to load the data
        cls=None, # Class of the newly created `DataLoader` object
        **kwargs
    ):
        res = super().new(dataset, cls, do_setup=False, **kwargs)
        if not hasattr(self, '_n_inp') or not hasattr(self, '_types'):
            try:
                self._one_pass()
                res._n_inp,res._types = self._n_inp,self._types
            except: print("Could not do one pass in your dataloader, there is something wrong in it")
        else: res._n_inp,res._types = self._n_inp,self._types
        return res

    def before_iter(self):
        super().before_iter()
        split_idx = getattr(self.dataset, 'split_idx', None)
        for nm in _batch_tfms:
            f = getattr(self,nm)
            if isinstance(f,Pipeline): f.split_idx=split_idx

    def decode(self,
        b # Batch to decode
    ):
        return to_cpu(self.after_batch.decode(self._retain_dl(b)))
    def decode_batch(self,
        b, # Batch to decode
        max_n:int=9, # Maximum number of items to decode
        full:bool=True # Whether to decode all transforms. If `False`, decode up to the point the item knows how to show itself
    ):
        return self._decode_batch(self.decode(b), max_n, full)

    def _decode_batch(self, b, max_n=9, full=True):
        f = self.after_item.decode
        f1 = self.before_batch.decode
        f = compose(f1, f, partial(getattr(self.dataset,'decode',noop), full = full))
        return L(batch_to_samples(b, max_n=max_n)).map(f)

    def _pre_show_batch(self, b, max_n=9):
        "Decode `b` to be ready for `show_batch`"
        b = self.decode(b)
        if hasattr(b, 'show'): return b,None,None
        its = self._decode_batch(b, max_n, full=False)
        if not is_listy(b): b,its = [b],L((o,) for o in its)
        return detuplify(b[:self.n_inp]),detuplify(b[self.n_inp:]),its

    def show_batch(self,
        b=None, # Batch to show
        max_n:int=9, # Maximum number of items to show
        ctxs=None, # List of `ctx` objects to show data. Could be matplotlib axis, DataFrame etc
        show:bool=True, # Whether to display data
        unique:bool=False, # Whether to show only one
        **kwargs
    ):
        "Show `max_n` input(s) and target(s) from the batch."
        if unique:
            old_get_idxs = self.get_idxs
            self.get_idxs = lambda: Inf.zeros
        if b is None: b = self.one_batch()
        if not show: return self._pre_show_batch(b, max_n=max_n)
        show_batch(*self._pre_show_batch(b, max_n=max_n), ctxs=ctxs, max_n=max_n, **kwargs)
        if unique: self.get_idxs = old_get_idxs

    def show_results(self,
        b, # Batch to show results for
        out, # Predicted output from model for the batch
        max_n:int=9, # Maximum number of items to show
        ctxs=None, # List of `ctx` objects to show data. Could be matplotlib axis, DataFrame etc
        show:bool=True, # Whether to display data
        **kwargs
    ):
        "Show `max_n` results with input(s), target(s) and prediction(s)."
        x,y,its = self.show_batch(b, max_n=max_n, show=False)
        b_out = type(b)(b[:self.n_inp] + (tuple(out) if is_listy(out) else (out,)))
        x1,y1,outs = self.show_batch(b_out, max_n=max_n, show=False)
        res = (x,x1,None,None) if its is None else (x, y, its, outs.itemgot(slice(self.n_inp,None)))
        if not show: return res
        show_results(*res, ctxs=ctxs, max_n=max_n, **kwargs)

    @property
    def n_inp(self) -> int:
        "Number of elements in `Datasets` or `TfmdDL` tuple to be considered part of input."
        if hasattr(self.dataset, 'n_inp'): return self.dataset.n_inp
        if not hasattr(self, '_n_inp'): self._one_pass()
        return self._n_inp

    def to(self,
        device # Device to put `DataLoader` and transforms
    ):
        self.device = device
        for tfm in self.after_batch.fs:
            for a in L(getattr(tfm, 'parameters', None)): setattr(tfm, a, getattr(tfm, a).to(device))
        return self

# Cell
add_docs(TfmdDL,
         decode="Decode `b` using `tfms`",
         decode_batch="Decode `b` entirely",
         new="Create a new version of self with a few changed attributes",
         show_batch="Show `b` (defaults to `one_batch`), a list of lists of pipeline outputs (i.e. output of a `DataLoader`)",
         show_results="Show each item of `b` and `out`",
         before_iter="override",
         to="Put self and its transforms state on `device`")

# Cell
@docs
class DataLoaders(GetAttr):
    "Basic wrapper around several `DataLoader`s."
    _default='train'
    def __init__(self,
        *loaders, # `DataLoader` objects to wrap
        path:(str,Path)='.', # Path to store export objects
        device=None # Device to put `DataLoaders`
    ):
        self.loaders,self.path = list(loaders),Path(path)
        if device is not None or hasattr(loaders[0],'to'): self.device = device

    def __getitem__(self, i): return self.loaders[i]
    def new_empty(self):
        loaders = [dl.new(dl.dataset.new_empty()) for dl in self.loaders]
        return type(self)(*loaders, path=self.path, device=self.device)

    def _set(i, self, v): self.loaders[i] = v
    train   ,valid    = add_props(lambda i,x: x[i], _set)
    train_ds,valid_ds = add_props(lambda i,x: x[i].dataset)

    @property
    def device(self): return self._device

    @device.setter
    def device(self,
        d # Device to put `DataLoaders`
    ):
        for dl in self.loaders: dl.to(d)
        self._device = d

    def to(self,
        device # Device to put `DataLoaders`
    ):
        self.device = device
        return self

    def _add_tfms(self, tfms, event, dl_idx):
        "Adds `tfms` to `event` on `dl`"
        if(isinstance(dl_idx,str)): dl_idx = 0 if(dl_idx=='train') else 1
        dl_tfms = getattr(self[dl_idx], event)
        apply(dl_tfms.add, tfms)

    def add_tfms(self,
        tfms, # List of `Transform`(s) or `Pipeline` to apply
        event, # When to run `Transform`. Events mentioned in `TfmdDL`
        loaders=None # List of `DataLoader` objects to add `tfms` to
    ):
        "Adds `tfms` to `events` on `loaders`"
        if(loaders is None): loaders=range(len(self.loaders))
        if not is_listy(loaders): loaders = listify(loaders)
        for loader in loaders:
            self._add_tfms(tfms,event,loader)

    def cuda(self): return self.to(device=default_device())
    def cpu(self):  return self.to(device=torch.device('cpu'))

    @classmethod
    def from_dsets(cls,
        *ds, # `Datasets` object(s)
        path:(str,Path)='.', # Path to put in `DataLoaders`
        bs:int=64, # Size of batch
        device=None, # Device to put `DataLoaders`
        dl_type=TfmdDL, # Type of `DataLoader`
        **kwargs
    ):
        default = (True,) + (False,) * (len(ds)-1)
        defaults = {'shuffle': default, 'drop_last': default}
        tfms = {k:tuple(Pipeline(kwargs[k]) for i in range_of(ds)) for k in _batch_tfms if k in kwargs}
        kwargs = merge(defaults, {k: tuplify(v, match=ds) for k,v in kwargs.items() if k not in _batch_tfms}, tfms)
        kwargs = [{k: v[i] for k,v in kwargs.items()} for i in range_of(ds)]
        return cls(*[dl_type(d, bs=bs, **k) for d,k in zip(ds, kwargs)], path=path, device=device)

    @classmethod
    def from_dblock(cls,
        dblock, # `DataBlock` object
        source, # Source of data. Can be `Path` to files
        path:(str, Path)='.', # Path to put in `DataLoaders`
        bs:int=64, # Size of batch
        val_bs:int=None, # Size of batch for validation `DataLoader`
        shuffle:bool=True, # Whether to shuffle data
        device=None, # Device to put `DataLoaders`
        **kwargs
    ):
        return dblock.dataloaders(source, path=path, bs=bs, val_bs=val_bs, shuffle=shuffle, device=device, **kwargs)

    _docs=dict(__getitem__="Retrieve `DataLoader` at `i` (`0` is training, `1` is validation)",
               train="Training `DataLoader`",
               valid="Validation `DataLoader`",
               train_ds="Training `Dataset`",
               valid_ds="Validation `Dataset`",
               to="Use `device`",
               add_tfms="Add `tfms` to `loaders` for `event",
               cuda="Use the gpu if available",
               cpu="Use the cpu",
               new_empty="Create a new empty version of `self` with the same transforms",
               from_dblock="Create a dataloaders from a given `dblock`")

# Cell
class FilteredBase:
    "Base class for lists with subsets"
    _dl_type,_dbunch_type = TfmdDL,DataLoaders
    def __init__(self, *args, dl_type=None, **kwargs):
        if dl_type is not None: self._dl_type = dl_type
        self.dataloaders = delegates(self._dl_type.__init__)(self.dataloaders)
        super().__init__(*args, **kwargs)

    @property
    def n_subsets(self): return len(self.splits)
    def _new(self, items, **kwargs): return super()._new(items, splits=self.splits, **kwargs)
    def subset(self): raise NotImplemented

    def dataloaders(self,
        bs:int=64, # Size of batch
        shuffle_train:bool=None, # Whether to shuffle training `DataLoader`
        shuffle:bool=True, # Whether to shuffle training `DataLoader`
        val_shuffle:bool=False, # Whether to shuffle validation `DataLoader`
        n:int=None, # Size of `Datasets` used to create `DataLoader`
        path:(str, Path)='.', # Path to put `DataLoaders`
        dl_type=None, # Type of `DataLoader`
        dl_kwargs=None, # Keyword arguments for individual `DataLoader`s
        device=None, # Device to put `DataLoaders`
        drop_last:bool=None, # Whether to drop last incomplete batch
        val_bs:int=None, # Size of batch for validation `DataLoader`
        **kwargs
    ):
        if shuffle_train is not None:
            shuffle=shuffle_train
            warnings.warn('`shuffle_train` is deprecated. Use `shuffle` instead.',DeprecationWarning)
        if device is None: device=default_device()
        if dl_kwargs is None: dl_kwargs = [{}] * self.n_subsets
        if dl_type is None: dl_type = self._dl_type
        if drop_last is None: drop_last = shuffle
        val_kwargs={k[4:]:v for k,v in kwargs.items() if k.startswith('val_')}
        def_kwargs = {'bs':bs,'shuffle':shuffle,'drop_last':drop_last,'n':n,'device':device}
        dl = dl_type(self.subset(0), **merge(kwargs,def_kwargs, dl_kwargs[0]))
        def_kwargs = {'bs':bs if val_bs is None else val_bs,'shuffle':val_shuffle,'n':None,'drop_last':False}
        dls = [dl] + [dl.new(self.subset(i), **merge(kwargs,def_kwargs,val_kwargs,dl_kwargs[i]))
                      for i in range(1, self.n_subsets)]
        return self._dbunch_type(*dls, path=path, device=device)

FilteredBase.train,FilteredBase.valid = add_props(lambda i,x: x.subset(i))

# Cell
class TfmdLists(FilteredBase, L, GetAttr):
    "A `Pipeline` of `tfms` applied to a collection of `items`"
    _default='tfms'
    def __init__(self,
        items, # List of items to apply `Transform`s to
        tfms, # List of `Transform`(s) or `Pipeline` to apply
        use_list:bool=None, # Whether to use `list` in `L`
        do_setup:bool=True, # Whether to call `setup()` for `Transform`
        split_idx:int=None, # Whether to apply `Transform`(s) to training or validation set. `0` for training set and `1` for validation set
        train_setup:bool=True, # Whether to apply `Transform`(s) only on training `DataLoader`
        splits:list=None, # List of indexs for for training and validation sets
        types=None, # Types of data in `items`
        verbose:bool=False, # Whether to print verbose output
        dl_type=None # Type of `DataLoader`
    ):
        super().__init__(items, use_list=use_list)
        if dl_type is not None: self._dl_type = dl_type
        self.splits = L([slice(None),[]] if splits is None else splits).map(mask2idxs)
        if isinstance(tfms,TfmdLists): tfms = tfms.tfms
        if isinstance(tfms,Pipeline): do_setup=False
        self.tfms = Pipeline(tfms, split_idx=split_idx)
        store_attr('types,split_idx')
        if do_setup:
            pv(f"Setting up {self.tfms}", verbose)
            self.setup(train_setup=train_setup)

    def _new(self, items, split_idx=None, **kwargs):
        split_idx = ifnone(split_idx,self.split_idx)
        return super()._new(items, tfms=self.tfms, do_setup=False, types=self.types, split_idx=split_idx, **kwargs)
    def subset(self, i): return self._new(self._get(self.splits[i]), split_idx=i)
    def _after_item(self, o): return self.tfms(o)
    def __repr__(self): return f"{self.__class__.__name__}: {self.items}\ntfms - {self.tfms.fs}"
    def __iter__(self): return (self[i] for i in range(len(self)))
    def show(self, o, **kwargs): return self.tfms.show(o, **kwargs)
    def decode(self, o, **kwargs): return self.tfms.decode(o, **kwargs)
    def __call__(self, o, **kwargs): return self.tfms.__call__(o, **kwargs)
    def overlapping_splits(self): return L(Counter(self.splits.concat()).values()).filter(gt(1))
    def new_empty(self): return self._new([])

    def setup(self,
        train_setup:bool=True # Whether to apply `Transform`(s) only on training `DataLoader`
    ):
        self.tfms.setup(self, train_setup)
        if len(self) != 0:
            x = super().__getitem__(0) if self.splits is None else super().__getitem__(self.splits[0])[0]
            self.types = []
            for f in self.tfms.fs:
                self.types.append(getattr(f, 'input_types', type(x)))
                x = f(x)
            self.types.append(type(x))
        types = L(t if is_listy(t) else [t] for t in self.types).concat().unique()
        self.pretty_types = '\n'.join([f'  - {t}' for t in types])

    def infer_idx(self, x):
        # TODO: check if we really need this, or can simplify
        idx = 0
        for t in self.types:
            if isinstance(x, t): break
            idx += 1
        types = L(t if is_listy(t) else [t] for t in self.types).concat().unique()
        pretty_types = '\n'.join([f'  - {t}' for t in types])
        assert idx < len(self.types), f"Expected an input of type in \n{pretty_types}\n but got {type(x)}"
        return idx

    def infer(self, x):
        return compose_tfms(x, tfms=self.tfms.fs[self.infer_idx(x):], split_idx=self.split_idx)

    def __getitem__(self, idx):
        res = super().__getitem__(idx)
        if self._after_item is None: return res
        return self._after_item(res) if is_indexer(idx) else res.map(self._after_item)

# Cell
add_docs(TfmdLists,
         setup="Transform setup with self",
         decode="From `Pipeline`",
         show="From `Pipeline`",
         overlapping_splits="All splits that are in more than one split",
         subset="New `TfmdLists` with same tfms that only includes items in `i`th split",
         infer_idx="Finds the index where `self.tfms` can be applied to `x`, depending on the type of `x`",
         infer="Apply `self.tfms` to `x` starting at the right tfm depending on the type of `x`",
         new_empty="A new version of `self` but with no items")

# Cell
def decode_at(o, idx):
    "Decoded item at `idx`"
    return o.decode(o[idx])

# Cell
def show_at(o, idx, **kwargs):
    "Show item at `idx`",
    return o.show(o[idx], **kwargs)

# Cell
@docs
@delegates(TfmdLists)
class Datasets(FilteredBase):
    "A dataset that creates a tuple from each `tfms`"
    def __init__(self,
        items:list=None, # List of items to create `Datasets`
        tfms:(list,Pipeline)=None, # List of `Transform`(s) or `Pipeline` to apply
        tls:TfmdLists=None, # If None, `self.tls` is generated from `items` and `tfms`
        n_inp:int=None, # Number of elements in `Datasets` tuple that should be considered part of input
        dl_type=None, # Default type of `DataLoader` used when function `FilteredBase.dataloaders` is called
        **kwargs
    ):
        super().__init__(dl_type=dl_type)
        self.tls = L(tls if tls else [TfmdLists(items, t, **kwargs) for t in L(ifnone(tfms,[None]))])
        self.n_inp = ifnone(n_inp, max(1, len(self.tls)-1))

    def __getitem__(self, it):
        res = tuple([tl[it] for tl in self.tls])
        return res if is_indexer(it) else list(zip(*res))

    def __getattr__(self,k): return gather_attrs(self, k, 'tls')
    def __dir__(self): return super().__dir__() + gather_attr_names(self, 'tls')
    def __len__(self): return len(self.tls[0])
    def __iter__(self): return (self[i] for i in range(len(self)))
    def __repr__(self): return coll_repr(self)
    def decode(self, o, full=True): return tuple(tl.decode(o_, full=full) for o_,tl in zip(o,tuplify(self.tls, match=o)))
    def subset(self, i): return type(self)(tls=L(tl.subset(i) for tl in self.tls), n_inp=self.n_inp)
    def _new(self, items, *args, **kwargs): return super()._new(items, tfms=self.tfms, do_setup=False, **kwargs)
    def overlapping_splits(self): return self.tls[0].overlapping_splits()
    def new_empty(self): return type(self)(tls=[tl.new_empty() for tl in self.tls], n_inp=self.n_inp)
    @property
    def splits(self): return self.tls[0].splits
    @property
    def split_idx(self): return self.tls[0].tfms.split_idx
    @property
    def items(self): return self.tls[0].items
    @items.setter
    def items(self, v):
        for tl in self.tls: tl.items = v

    def show(self, o, ctx=None, **kwargs):
        for o_,tl in zip(o,self.tls): ctx = tl.show(o_, ctx=ctx, **kwargs)
        return ctx

    @contextmanager
    def set_split_idx(self, i):
        old_split_idx = self.split_idx
        for tl in self.tls: tl.tfms.split_idx = i
        try: yield self
        finally:
            for tl in self.tls: tl.tfms.split_idx = old_split_idx

    _docs=dict(
        decode="Compose `decode` of all `tuple_tfms` then all `tfms` on `i`",
        show="Show item `o` in `ctx`",
        dataloaders="Get a `DataLoaders`",
        overlapping_splits="All splits that are in more than one split",
        subset="New `Datasets` that only includes subset `i`",
        new_empty="Create a new empty version of the `self`, keeping only the transforms",
        set_split_idx="Contextmanager to use the same `Datasets` with another `split_idx`"
    )

# Cell
def test_set(
    dsets:(Datasets, TfmdLists), # Map- or iterable-style dataset from which to load the data
    test_items, # Items in test dataset
    rm_tfms=None, # Start index of `Transform`(s) from validation set in `dsets` to apply
    with_labels:bool=False # Whether the test items contain labels
):
    "Create a test set from `test_items` using validation transforms of `dsets`"
    if isinstance(dsets, Datasets):
        tls = dsets.tls if with_labels else dsets.tls[:dsets.n_inp]
        test_tls = [tl._new(test_items, split_idx=1) for tl in tls]
        if rm_tfms is None: rm_tfms = [tl.infer_idx(get_first(test_items)) for tl in test_tls]
        else:               rm_tfms = tuplify(rm_tfms, match=test_tls)
        for i,j in enumerate(rm_tfms): test_tls[i].tfms.fs = test_tls[i].tfms.fs[j:]
        return Datasets(tls=test_tls)
    elif isinstance(dsets, TfmdLists):
        test_tl = dsets._new(test_items, split_idx=1)
        if rm_tfms is None: rm_tfms = dsets.infer_idx(get_first(test_items))
        test_tl.tfms.fs = test_tl.tfms.fs[rm_tfms:]
        return test_tl
    else: raise Exception(f"This method requires using the fastai library to assemble your data. Expected a `Datasets` or a `TfmdLists` but got {dsets.__class__.__name__}")

# Cell
@patch
@delegates(TfmdDL.__init__)
def test_dl(self:DataLoaders,
    test_items, # Items in test dataset
    rm_type_tfms=None, # Start index of `Transform`(s) from validation set in `dsets` to apply
    with_labels:bool=False, # Whether the test items contain labels
    **kwargs
):
    "Create a test dataloader from `test_items` using validation transforms of `dls`"
    test_ds = test_set(self.valid_ds, test_items, rm_tfms=rm_type_tfms, with_labels=with_labels
                      ) if isinstance(self.valid_ds, (Datasets, TfmdLists)) else test_items
    return self.valid.new(test_ds, **kwargs)