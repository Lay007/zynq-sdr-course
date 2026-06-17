#include "stdio.h"
#include "sleep.h"
#include "xparameters.h"
#include "xil_printf.h"
#include "xstatus.h"
#include "ff.h"


#define FILE_NAME "ZXK.txt"						//定义文件名
const char Test_Char[30] = "hello sd card test";//写入字符串
static FATFS fatfs;								//文件系统

int platform_init_fs()
{
	FRESULT status;
	TCHAR *path = "0:/";
	BYTE work[FF_MAX_SS];
	//挂载文件系统
	status = f_mount(&fatfs, path, 1);
	if(status != FR_OK)
	{
		xil_printf("Volume is not formated;formating FAT\r\n");
		//格式化SD卡
		status = f_mkfs(path, FM_FAT32, 0, work, sizeof work);
		if(status != FR_OK)
		{
			xil_printf("Unable to format Fatfs\r\n");
			return -1;
		}
		//格式化之后，重新挂载
		status = f_mount(&fatfs, path, 1);
		if(status != FR_OK)
		{
			xil_printf("Unable to format Fatfs\r\n");
			return -1;
		}
	}
	return 0;
}

int EMMC_mount()
{
	FRESULT status;
	status = platform_init_fs();
	if(status==-1)
	{
		xil_printf("ERROR:f_mount return %d!\r\n",status);
		return XST_FAILURE;
	}
	return XST_SUCCESS;
}

int EMMC_write_data(char *file_Name,u32 src_addr,u32 byte_len)
{
	FIL fil;		//文件对象
	UINT bw;		//f_write函数返回已写入的字节数
	//打开一个文件，如果不存在则创建
	f_open(&fil, file_Name, FA_CREATE_ALWAYS | FA_WRITE);
	//移动打开的文件对象的文件读写指针
	f_lseek(&fil, 0);
	//项文件中写入数据
	f_write(&fil, (void*)src_addr, byte_len, &bw);
	//关闭文件
	f_close(&fil);
	return 0;
}

//SD卡读数据
int EMMC_read_data(char *file_Name,u32 src_addr,u32 byte_len)
{
	FIL fil;		//文件对象
	UINT br;		//f_read函数返回已读出的字节数
	//打开一个只读文件
	f_open(&fil, file_Name, FA_READ);
	//移动打开的文件对象的文件读写指针
	f_lseek(&fil, 0);
	//项文件中写入数据
	f_read(&fil, (void*)src_addr, byte_len, &br);
	//关闭文件
	f_close(&fil);
	return 0;
}


int main()
{
	int status,len;
	char dest_str[30] = "";
	status = EMMC_mount();
	if(status!=XST_SUCCESS)
	{
		xil_printf("Failed to open EMMC\r\n");
		return 0;
	}
	else
	{
		xil_printf("Success to open EMMC\r\n");
	}

	//写入读出测试
	len = strlen(Test_Char);		//计算字符串长度
	//EMMC写数据
	EMMC_write_data(FILE_NAME, (u32)Test_Char, len);
	//SD卡读数据
	EMMC_read_data(FILE_NAME, (u32)dest_str, len);

	//数据校验
	if(strcmp(Test_Char,dest_str) == 0)
	{
		xil_printf("src_str is equal to dest_str,EMMC test success\r\n");
	}
	else
	{
		xil_printf("src_str is not equal to dest_str,EMMC test failed\r\n");
	}

	while(1)
	{
		printf("Hello\r\n");
		sleep(1);
	}
	return 0;
}
