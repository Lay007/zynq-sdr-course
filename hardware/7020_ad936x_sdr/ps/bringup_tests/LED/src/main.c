#include "stdio.h"
#include "sleep.h"
#include "xparameters.h"
#include "xgpiops.h"


#define GPIO_DEVICE_ID		XPAR_XGPIOPS_0_DEVICE_ID
#define LED_GPIO_PIN		0


int main()
{
	/* Initialize the GPIO driver. */
	XGpioPs_Config *ConfigPtr;
	ConfigPtr = XGpioPs_LookupConfig(GPIO_DEVICE_ID);
	/* The driver instance for GPIO Device. */
	XGpioPs Gpio;
	XGpioPs_CfgInitialize(&Gpio, ConfigPtr,ConfigPtr->BaseAddr);
	/*
	 * Set the direction for the pin to be output and
	 * Enable the Output enable for the LED Pin.
	 * */
	XGpioPs_SetDirectionPin(&Gpio, LED_GPIO_PIN, 1);
	XGpioPs_SetOutputEnablePin(&Gpio, LED_GPIO_PIN, 1);

	while(1)
	{
		/* Set the GPIO output to be high. */
		XGpioPs_WritePin(&Gpio, LED_GPIO_PIN, 0x1);
		sleep(1);
		printf("Hello World\r\n");
		/* Set the GPIO output to be low. */
		XGpioPs_WritePin(&Gpio, LED_GPIO_PIN, 0x0);
		sleep(1);
	}
	return 0;
}
