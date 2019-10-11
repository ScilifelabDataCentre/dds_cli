# AES-GCM

* Standardized by NIST (National Institute of Standards and Technology)
* One of the fastest encryption modes
* Used by TLS, IPSec, OpenVPN etc
* Parallelizable
* On-line 
	* Size of data not needed in advance
* Allows for parallel encrypted data streaming

## Authenticated Encryption (AE) with Associated Data (AEAD) mode
Provides

* Confidentiality
* Integrity
* Authenticity 

Decryption combined wih integrity verification

## Optimal parameters
* **Key**: 256 bits
* **IV**: 96 bits
	1. 96 bit counter initialized to 0 
	2. Deterministic IV: 
		* Fixed 32 bit field: Context identifier.
			* If key reused: Each context different
			* New key generated for each file: Context can be static - key/IV reuse inlikely and depend on generating duplicate encryption key.
		* 64 bit invocation field: Counter initialized to 0. Incremented for each block. 
	3. Random IV:
		* Generate random 96 bit IV from CSPRNG (cryptographically secure random number generator). 
		* Same key can be reused as long as a new IV i generated for each encryption operation and the IV is guarateed to be unique. 
		* **NOT RECOMMENDED TO BE USED** - security is hrder to prove. 
* **Tag**: 128 bits
* *Maximum encrypted plaintext size*: 2^39 - 156 bits = **68,7 GB**
