# -*- coding: utf-8 -*-

""" 
Volume Segmentation

Team Challenge Group 2
R.E. Buijs, D.M Cornelissen, D. Devetzis, D. Le, J. Zhang
Utrecht University & University of Technology Eindhoven

""" 

from torch.utils.data import Dataset
from torchvision.transforms import v2
import nibabel as nib
import torch
import numpy as np
import glob
import scienceplots
import matplotlib.pyplot as plt
import SimpleITK as sitk
import zipfile
import pydicom
from matplotlib.widgets import Button, Slider

class Dataset(Dataset):
    """
    Dataset class to load and preprocess image data from file. 
    Inherited and adheres to torch.Dataset superclass.

    Arguments:
        Dataset -- torch.Dataset object
    """    

    def __init__(self, config):
        data_dir = config["dataloader"]["data_dir"]
        self.extension = config["dataloader"]["extension"]
        self.normalize = config["dataloader"]["normalize"]
        self.data_paths = self.dir_to_list(data_dir)
        self.length = len(self.data_paths)
        self.transforms = [None]
        self.seed = np.random.randint(2147483647) 
        
    def dir_to_list(self, data_dir):
        """
        Retrieves path from data directory and returns as list of [img, mask].

        Parameters
        ----------
        data_dir : String
            Directory path to image data.

        Returns
        -------
        data : List
            List of [image path, mask path] for each image.

        """
        file_list = glob.glob(data_dir + "*")
        # data = []
        # for file_path in file_list:
        #     file_name = file_path.split("\\")[1]
        #     data.append([file_path + "\\" + file_name + self.extension,
        #                  file_path + "\\" + file_name + "_seg" + self.extension])
        #     # data.append([file_path + "\\" + file_name + ".dcm",
        #     #              file_path + "\\" + file_name + ".dcm"])
        # print(f"Total of {len(data)} images found.")
        data = list()
        for file_path in file_list:
            file_name_original = glob.glob(file_path+"/"+"*.zip")[0]
            #need to change the format of label file (original image and label should be in the same path for each patient)
            file_name_label= glob.glob(file_path+"/"+"*.zip")[0] # segmentation mask
            data.append([file_name_original,file_name_label])
        return data
    
    def __len__(self):
        return self.length

    def __getitem__(self, index):
        """
        @override
        Method which returns image and mask data by index, modified to perform 
        intended transformation.
        
        Parameters
        ----------
        index : Integer
            Natural number. Index of image in dataset.

        Returns
        -------
        img
            Torch image tensor.
        mask
            Torch mask tensor.
            
        """
        assert index < self.length, \
            f"index should be smaller than {self.length}"
        index_transforms = index // len(self.data_paths)
        transform = self.transforms[index_transforms]
    
        if index >= len(self.data_paths):
            index = (index - len(self.data_paths)) % len(self.data_paths)
                
        img, mask = self.path_to_tensor(self.data_paths[index])
        
        if transform is not None:
            torch.manual_seed(self.seed + index)
            state = torch.get_rng_state()
            img = transform(img)
            torch.set_rng_state(state)
            mask = transform(mask)
            
        if self.normalize:
            img -= torch.min(img)
            img /= torch.max(img)
                                      
        # print(f"Transform: {transform}")
        # print(f"Index true: {index}")
            
        return img, mask
    
    def collate_fn(self, batch):
        """Collate (collect and combine) function for varying input size."""
        return batch
    
    def path_to_tensor(self, file_name):
        """
        Extracts tensor data from .dcm or .nii.gz files

        Parameters
        ----------
        filename : string
            Path to .dcm or .nii.gz file.

        Returns
        -------
        tensor_data : Tensor
            Tensor object of torch module containing image data.

        """
        output = list()
        with zipfile.ZipFile(file_name[0],'r') as zipf:
            img_data = list()
            zipf.extractall()
            ls= zipf.infolist()
            instance_numbers = list()
            for i, slice in enumerate(ls):
                slice_data = pydicom.read_file(slice.filename)
                if "DICOM" in zipf.namelist()[i]:
                    instance_numbers.append(slice_data[0x20,0x13].value)
                    img_data.append(slice_data.pixel_array)
            instance_numbers = list(map(int, instance_numbers))
            img_data = [x for y, x in sorted(zip(instance_numbers, img_data))]
            img_data = np.stack(img_data).astype('float32')

        with zipfile.ZipFile(file_name[1],'r') as zipf:
            mask_data = list()
            zipf.extractall()
            ls= zipf.infolist()
            instance_numbers = list()
            for i, slice in enumerate(ls):
                slice_data = pydicom.read_file(slice.filename)
                if "DICOM" in zipf.namelist()[i]:
                    instance_numbers.append(slice_data[0x20,0x13].value)
                    mask_data.append(slice_data.pixel_array)
            instance_numbers = list(map(int, instance_numbers))
            mask_data = [x for y, x in sorted(zip(instance_numbers, mask_data))]
            mask_data = np.stack(mask_data).astype('float32')
            
        return torch.from_numpy(img_data), torch.from_numpy(mask_data)
    
    def augment_all(self, transform):
        """
        Artificially increases dataset length and saves transform.

        Parameters
        ----------
        transform : torchvision.transforms.v2 module
            A data transformation module from Torchvision

        Returns
        -------
        None.

        """
        self.length += len(self.data_paths)
        self.transforms.append(transform)
        print(f"Total images: {self.length}")
    
    def plot(self, index, slice=(slice(None), slice(None))):
        
        """Plot image data and mask."""
        img, mask = self.__getitem__(index)
        plt.style.use(['science','ieee', 'no-latex'])
        fig, axes = plt.subplots(2, 1)
        plt.setp(plt.gcf().get_axes(), xticks=[], yticks=[]);
        plt.rcParams["font.family"] = "Arial"
        axes[0].imshow(img[12,:,:], cmap='gray')
        axes[0].title.set_text(f"Image {index}")
        axes[1].imshow(mask[12,:,:], cmap='rainbow', alpha=0.5)
        axes[1].title.set_text(f"Mask {index}")
        plt.subplots_adjust(hspace=0.3)
        plt.show()
        
            
    