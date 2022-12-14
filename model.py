from torch import nn, Tensor
from typing import List, Optional, Tuple

def _make_layer(
    in_channels: int, 
    out_channels: int
) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True)
    )

class _EncBlock(nn.Module):
    def __init__(
        self, 
        in_channels: int, 
        out_channels: int, 
        num_layers: int
    ) -> None:
        super().__init__()
        layers = [_make_layer(in_channels, out_channels)]
        for _ in range(num_layers - 1):
            layers += [_make_layer(out_channels, out_channels)]
        self.layers = nn.Sequential(*layers)
        self.max_pool = nn.MaxPool2d(kernel_size=2, stride=2, return_indices=True)
        
    def forward(self, x: Tensor) -> Tuple[Tensor, Tensor]:
        x = self.layers(x)
        x, indices = self.max_pool(x)
        return x, indices
    
class _BayesEncBlock(_EncBlock):
    def __init__(
        self, 
        in_channels: int, 
        out_channels: int, 
        num_layers: int
    ) -> None:
        super().__init__(in_channels, out_channels, num_layers)
        self.dropout = nn.Dropout2d(0.5, inplace=False)
        
    def forward(self, x: Tensor) -> Tuple[Tensor, Tensor]:
        x, indices = super().forward(x)
        x = self.dropout(x)
        return x, indices
    
class _DecBlock(nn.Module):
    def __init__(
        self, 
        in_channels: int, 
        out_channels: int, 
        num_layers: int
    ) -> None:
        super().__init__()
        self.max_unpool = nn.MaxUnpool2d(kernel_size=2, stride=2)
        layers = []
        for _ in range(num_layers - 1):
            layers += [_make_layer(in_channels, in_channels)]
        layers += [_make_layer(in_channels, out_channels)]
        self.layers = nn.Sequential(*layers)
        
    def forward(
        self, x: Tensor, 
        indices: Tensor, 
        output_size: Optional[List[int]] = None
    ) -> Tensor:
        x = self.max_unpool(x, indices, output_size)
        x = self.layers(x)
        return x
    
class _BayesDecBlock(_DecBlock):
    def __init__(
        self, 
        in_channels: int, 
        out_channels: int, 
        num_layers: int
    ) -> None:
        super().__init__(in_channels, out_channels, num_layers)
        self.dropout = nn.Dropout2d(0.5, inplace=False)
        
    def forward(
        self, 
        x: Tensor, 
        indices: Tensor, 
        output_size: Optional[List[int]] = None
    ) -> Tensor:
        x = super().forward(x, indices, output_size)
        x = self.dropout(x)
        return x

class SegNet(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.encoder0 = _EncBlock(in_channels, 64, 2)
        self.encoder1 = _EncBlock(64, 128, 2)
        self.encoder2 = _EncBlock(128, 256, 3)
        self.encoder3 = _EncBlock(256, 512, 3)
        self.encoder4 = _EncBlock(512, 512, 3)
        
        self.decoder4 = _DecBlock(512, 512, 3)
        self.decoder3 = _DecBlock(512, 256, 3)
        self.decoder2 = _DecBlock(256, 128, 3)
        self.decoder1 = _DecBlock(128, 64, 2)
        self.decoder0 = _DecBlock(64, 64, 1)
        
        self.conv = nn.Conv2d(64, out_channels, kernel_size=3, padding=1)
        self.softmax = nn.Softmax2d()
        
    def forward(self, x: Tensor) -> Tensor:
        dim0 = x.size()
        x, indices0 = self.encoder0(x)
        dim1 = x.size()
        x, indices1 = self.encoder1(x)
        dim2 = x.size()
        x, indices2 = self.encoder2(x)
        dim3 = x.size()
        x, indices3 = self.encoder3(x)
        dim4 = x.size()
        x, indices4 = self.encoder4(x)
        
        x = self.decoder4(x, indices4, dim4)
        x = self.decoder3(x, indices3, dim3)
        x = self.decoder2(x, indices2, dim2)
        x = self.decoder1(x, indices1, dim1)
        x = self.decoder0(x, indices0, dim0)
        x = self.conv(x)
        x = self.softmax(x)
        return x
    
class BayesEncoderSegNet(SegNet):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__(in_channels, out_channels)
        self.encoder0 = _BayesEncBlock(in_channels, 64, 2)
        self.encoder1 = _BayesEncBlock(64, 128, 2)
        self.encoder2 = _BayesEncBlock(128, 256, 3)
        self.encoder3 = _BayesEncBlock(256, 512, 3)
        self.encoder4 = _BayesEncBlock(512, 512, 3)
        
# class BayesDecoderSegNet(SegNet):
#     def __init__(self, in_channels: int, out_channels: int) -> None:
#         super().__init__(in_channels, out_channels)
#         self.decoder4 = BayesDecBlock(512, 512, 3)
#         self.decoder3 = BayesDecBlock(512, 256, 3)
#         self.decoder2 = BayesDecBlock(256, 128, 3)
#         self.decoder1 = BayesDecBlock(128, 64, 2)
#         self.decoder0 = BayesDecBlock(64, 64, 1)
        
class BayesCenterSegNet(SegNet):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__(in_channels, out_channels)
        self.encoder2 = _BayesEncBlock(128, 256, 3)
        self.encoder3 = _BayesEncBlock(256, 512, 3)
        self.encoder4 = _BayesEncBlock(512, 512, 3)
        
        self.decoder4 = _BayesDecBlock(512, 512, 3)
        self.decoder3 = _BayesDecBlock(512, 256, 3)
        self.decoder2 = _BayesDecBlock(256, 128, 3)
        
# class BayesEncoderDecoder(SegNet):
#     def __init__(self, in_channels: int, out_channels: int) -> None:
#         self.encoder0 = _BayesEncBlock(in_channels, 64, 2)
#         self.encoder1 = _BayesEncBlock(64, 128, 2)
#         self.encoder2 = _BayesEncBlock(128, 256, 3)
#         self.encoder3 = _BayesEncBlock(256, 512, 3)
#         self.encoder4 = _BayesEncBlock(512, 512, 3)
        
#         self.decoder4 = BayesDecBlock(512, 512, 3)
#         self.decoder3 = BayesDecBlock(512, 256, 3)
#         self.decoder2 = BayesDecBlock(256, 128, 3)
#         self.decoder1 = BayesDecBlock(128, 64, 2)
#         self.decoder0 = BayesDecBlock(64, out_channels, 2)

if __name__ == "__main__":
    model = BayesCenterSegNet(3, 10)
    print(model)