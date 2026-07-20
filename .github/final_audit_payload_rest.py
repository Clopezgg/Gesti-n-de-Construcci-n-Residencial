#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_DATA = (
    'H4sIANErXmoC/5VRXWvCMBR9z6+4FFFwpLEwJwg+iOs2GbMSdR8wGLFN10LzQZI5RfzvBusQJsKWh3uScO45OTdDeg8xnU7i1/nH'
    'c0xn42QyWEXdMIp6YQfd0eQJcsO05oQbLfna9RvbX/wdQkOvMvcl9mX0gBazmIJRyiG6mIDj1kHQ2J4IfcxEdnO9C2AAwWEbwDsC'
    'v5pNYNrhT+7gS2fM8fP7UlrHqgrwBjCWCh/P2PBUCcFlZkEblWp7ajUCsMmBrJghVbkkXsqjdZa00SiZvnmhtFDfclBH7dcAIZBC'
    'CU6OA6gBL7lMCy+h7c9IDinzUmZ/5JOM60r557uNd8kBSyY4tNqhLVqA+ZqnkBZCZdDpdbuw3cHVKcp/bGxqSu0sYMHW3tIVEJ17'
    '6s0FT1R/Yy2PXhL6eDuml63RHnM6TSBKAgAA'
)
_path = Path('Dockerfile')
_path.parent.mkdir(parents=True, exist_ok=True)
_path.write_bytes(gzip.decompress(base64.b64decode("".join(_DATA))))

_DATA = (
    'H4sIANErXmoC/6Vb6XLjxhH+r6eAkVQt6IjUErwkVslVpMS1WZZERYeTipaBQWIojQUCNA5JtKyqvEPyJnkEv0meJN1zNcBrd21V'
    'rfUBmOnu6elreuQ/fXWQp8nBhEcHLHqyFsvsIY4ae7MknlueN8uzPGGeZ/H5Ik4yy4+iOPMzHkfp3p5+l9wv/CRl+vmnNI40Tpik'
    'tPCzh5BPNJlLeJQfsuWCR/f6fS9a7lvDjCX+JGR7e+e9m6vh372T0dnt+cW1dWzdvRsGLMr4jE/9IE7e7VvvPuTwgiG6Yj/nPOVZ'
    'jA/nv/03yEMBh/NFyOYwyp/y3/4bWSyaxlGW+IGPX3vJ9IE/xSnik3g+5xmiyyRnE9+a5dEU1uqHhXcRuwcFPInJgyiLkyiW3NM8'
    'zEAqi6ULWECw8jaeZCzi8u3gicMyplzQGEbTHCTkcw4iis/X7IklPPADKVOSsKmU3IdhUyW3lNUKmDWlEWWWizgFVXKpp0GK796N'
    '93pnZ6O/DU6965vezQCV+mr3Lq9G/d7pyN637KvByXe9f6iHi5F1OjgfXd9cqReDC+tkdAVjToa//fvCftu7Gvz1dngF5NReDU+R'
    'pPPu29EP1fd1ZCyQa1DDoKZBLYPaBnUMOkR0e/2+rghK6BJsEGwSbBFsE+wQLNA9MrD+niBxqwtuH4ZGBgkLbxsEmwRbBNsEOwQP'
    'CR4ZKGWQkLgVZKgTtzpxq2tuLgnpkpAuCemSkC4J6ZKQLgnpkpAuCemSkC4J6ZKQLgnpkpBuUcg6casTtzpxqxM3V3C7vDIbIKFL'
    'sEGwSbBFsE2wQ/CQ4JGBcm0nI8NNQpdgg2CTYItgm2CH4CHBIwMlt/Nzw01Cl2CDYJNgi2BbQZcouETBJQouUXCJglui0CEo5D0f'
    'fjvSdAV0CTYINgm2CLYJdggW6B4ZKPXw1xOjBwldgg2CTYItgm2CHYKHBI8MVHt8Rnt8Rnt8Rnt8Rnt8Rnt8Rnt8Rnt8Zrj1KVT0'
    'KVT0KVT0KVT0KVT0KVT0KVT0hyt0jwyUq+jdGm4SugQbBJsEWwTbBDsEDwkeGagsddTX5oDINahhUNOglkFtgzoGHRp0pJHkcfm3'
    'nnZ0RK5BDYOaBrUMahvUMUjwuD75TtETyDWoYVDToJZBbYM6BhG9I42UXobfkpuQl5CTkI+Qi5CHkIOQf5B7KB6YjRUTCV2CDYJN'
    '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'
)
_path = Path('scripts/audit_requirements_1to1.py')
_path.parent.mkdir(parents=True, exist_ok=True)
_path.write_bytes(gzip.decompress(base64.b64decode("".join(_DATA))))

_DATA = (
    'H4sIANErXmoC/81X3W7bNhS+11MQ3I3UOcrc7mII4AGa7aIG6thIHGxYFjAMRadsJVIlKSdZ20faVR8hL7ZDUrIdOV6RohgqwLBE'
    'fefvO4fnUEutSkTIsra15oQgUVZKW0SlVJZaoaSJomYt/BXiKq2tKNpVy8tqKQrePtdSWMuNjZZOc0XtG5Bo1c7hMYqi6Wx09npM'
    '5tniFRr4xRhcACWEJKnmRhUrHidpRTWX1py/uECHCBumRWUNdve0zoUlmr+vhealA5G+Vf20usPR6Xw8BK0PvU1NxRlxLgU7hWI+'
    'uhgzRoI2pwD30JZvSUSN4eC2V0ll7m/SQtGc6yg7G00Wu4ZKlddgwJtyRmMnk0Rbkim/BV8CLvZaEuCEFWAMZYzxylLJ+JRaLW4z'
    '59oC6IxbXlP3NKSGJ0cRgivnS0S0UpbcCPuGlF4sNrxY9tCzHjKQRX4Efxpcxdn8ZPZbNppBnJJfAwOrzbtLp90ctuvA5SVO0MGv'
    'Pj/BlrtcvpWm+g5k2tyDT83iCPLBrNJ3cbKWcL6kNM+HBaeyruK1hpSFlQ3UxdFWxAYmack3mBAhoDwYiiFXzByCWahVq2vm0no4'
    'zRYnkz9JNhzPF9lwMjsm/ayfljnuqGlqLC3f5ULHTcENFrreMhi3hoxmOGmgj7z2/P0XAOQPQ9pdoSbpjRaWE8tvbYxXtKg5BNX/'
    'S0JyuGQqF/J6gGu7PPgF77N2uKylD5gWuyorKKinadvK/dN1MVXUpTQQg6/p1KfgDzKcvT6bHp9upfgGIB/Wz+7Ckxx4F0vBaK40'
    'PkJ4cfATbMaHoJc1gLh7O9OAh8pHFSTqinaBJ64vGGGVww6VtJpahVZcewtXBe8KTO8/Q1Y8fP6oxklZFb7PUCbuP0vPglObUyfT'
    'fas5LboaMs3eiJUyDn/5oBAuu9ChKkthHfDVOBshBh2ooaaLDM4iVwS+BrzyRwrjco9gk28XRJv6DnAsYTPLQORkl2dTFxb8Qhw6'
    'nXYOAi7zHcwzsV9AXVkuxY4A5LRUJhDb9WQlIOlMeMZ/V/rdsoBKukPUsUOZdeWw6+JEshqyI0oB6fHWjqF4a7lD5Sl39ZHT3Ieq'
    '7/+xwPhuZjT0meApBa2sKYCGTvBA82uYX4/FHrLqMGyjxQnTK9Z//uLn/VxVwAj4FjbG0IXDUf9oZ3uMjQ0Z8C1/8/LT+q4Qkrv9'
    'ef5Q8AfkZ83fXYXd548Iox/hB//pWyVk3Oz4JKzuwD36Y4M9xwcHB/gCPUMF30gmAfIlQ9AzzoPIBVoq3bQaJCTa68JFt9FvdzPo'
    'ZEGxZ8QLf6G5aQ7nI+lHTrQeu26nEeontiFMucSACVpVWq14vj2K/Rw9VpIfdUedH46783vbsquDdVeFOQFV6sysTwqtjFPSQ82h'
    'KCciN4MPoZF+6g5jf6xxUy4O6s99g+c5vuihdmVJRQFnQoMvHpUev69psRaHDBkn3E869Gj+Fg4EhtSyOdflxNfn19HiRQf4eIZG'
    '4+nsdHHizjL/B1cvaWF2ydpPK5V3Md7EHPYkdhULVVj6IvY3Qj7G9z4SS2EMlCdpmzXhoSl+JZutmgE+BT+aWfrdstmdWd+KzK2v'
    'CPD8e9iuPX/+ef4tyZuGYNFWsGgyMk8hMRLwoUHcWRw+EwfwwUAgEiEJwYGl9QeKWwVG/gUMe7vPWg4AAA=='
)
_path = Path('erpnext/construcontrol/tests/test_acceptance_matrix_audit_standalone.py')
_path.parent.mkdir(parents=True, exist_ok=True)
_path.write_bytes(gzip.decompress(base64.b64decode("".join(_DATA))))

_DATA = (
    'H4sIANErXmoC/6VUUW+bMBB+51ec/FLYAmiaJk1I2UvbqZPadWr7lkSWC0fi1Rhqm6z59zsTIKRKtUrzA8I++7vvO3/n0tQVcF62'
    'rjXIOciqqY0DoXXthJO1tkHQrxkc/lotnUPrgtKfboTbKPk4HP1F0yAI7m5vH2DezULCl4rQo8SgrdUWwyhphEHt7OLzijYXWMJW'
    'KFkIh7xZG2x4gQ3qAnW+C4s6f0LjITKwzswgrymV3c8iiL+BktYtaLLKAqBRCqlIjs0OAaKyWHVBWQLrUkBcMpB6ROui/Q5ST3oT'
    'i8Lkm3CM+GGYaFy8Rre0H6W2TihFf/HOf2Jdx/1abJCAK9JgKdKYOm8smx0hHXQd1qPsaMugJBGNL0fI9mfinjO0Fi3s1Ty2Di5G'
    'RAKniJfR84GeQjSVyUwFsSkh3QqT0h2mJC31NbPpB9afntD8B7dT2Q1W9RaBcMkn+ZNYI0EW+IIDE4PkPD2CkRlyJayFKxTKbfIN'
    '5k93rXaywovREQ/kvXAwYeJn58JiXzrvJb/OSXDR5o7LirJy2zaNkmh7exl8bqXBgj/u+OaQyoYWVdl56metJ4IPRSAnhZ25U5go'
    'Zt7bouAOX1xIHOtC6vWcta6Mv05qPtzbBOP4RpNdpd6J5ZkmVCo07vK5FSp8TweNzRPNqCGi4LhklbSWcvG9V7i0VKffmDss3qrL'
    'cG+k6O30R7Zh3+9ub6A03jUpmkaTymz76ctSv2qPs8m9ZEsNHcUMFuz85iK+v7q8vmazQyvDn9qQRrZa6rNJO52q1g/9itF/N9Xs'
    'ZGNMadArWtI7q0XlX9n5HBjnlZCac7Yv5mhnvxpGwV/PodqImQUAAA=='
)
_path = Path('erpnext/construcontrol/tests/test_healthcheck_runtime_dependency_standalone.py')
_path.parent.mkdir(parents=True, exist_ok=True)
_path.write_bytes(gzip.decompress(base64.b64decode("".join(_DATA))))

_DATA = (
    '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'
)
_path = Path('docs/reconstruction/CHECKPOINT.md')
_path.parent.mkdir(parents=True, exist_ok=True)
_path.write_bytes(gzip.decompress(base64.b64decode("".join(_DATA))))

_DATA = (
    'H4sIANErXmoC/1VQy27DIBC88xX8AA3OIa24uWkjWUqTqnIuvaAtXsdIvAo4Tf++2EkUVULDamBmZzepAS0IqrxLOY7lytEbpjBm'
    '3WsFWXvHIn6PmDI7VeRaCro5bLfkK4JTg6ARb3o1/e+w105nfQL235d8QUJBLWh3c8JOQrFb8uWK8Ue25C1/EpyXw/iqINE2GLTo'
    '8pxFTg5Gu+KCZ1CZhcgGhI6AUhhyiYPSQo76LGjnVVrco03yxVvdfjSfsl6/vrf1utnvZFVXD7YjR8iYBKGU0XrG5xnXM26aXb29'
    'vB1emlZWst3LsozRXDRzFDnlELS0wkJZjEeUIQrag0kz4zvd/8pp+DvZ+1gShzENd27ajI4owZjrLDL6nyQhhOhPeOvxB3SqQcq7'
    'AQAA'
)
_path = Path('docs/reconstruction/CERTIFICATION_REQUEST.yml')
_path.parent.mkdir(parents=True, exist_ok=True)
_path.write_bytes(gzip.decompress(base64.b64decode("".join(_DATA))))
