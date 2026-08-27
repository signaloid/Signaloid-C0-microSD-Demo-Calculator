/*
 *	Copyright (c) 2026, Signaloid.
 *
 *	Permission is hereby granted, free of charge, to any person obtaining a copy
 *	of this software and associated documentation files (the "Software"), to deal
 *	in the Software without restriction, including without limitation the rights
 *	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *	copies of the Software, and to permit persons to whom the Software is
 *	furnished to do so, subject to the following conditions:
 *
 *	The above copyright notice and this permission notice shall be included in all
 *	copies or substantial portions of the Software.
 *
 *	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *	SOFTWARE.
 */


#include <uxhw.h>
#include "C0HAL.h"


typedef enum
{
	kCalculateNoCommand         = 0,
	kCalculateAddition          = 1,
	kCalculateSubtraction       = 2,
	kCalculateMultiplication    = 3,
	kCalculateDivision          = 4,
	kCalculateSample            = 5,
} SignaloidSoCCommand;

enum
{
	kWeightedSampleCount = 16
};

/*
 *	Generate a distribution from weighted samples from a Gaussian distribution
 *	with mean value zero and standard deviation equal to one.
 */
WeightedFloatSample weightedSamples[kWeightedSampleCount] = {
	{ .sample = -2.2194097942437231, .sampleWeight = 0.0339789420851602 },
	{ .sample = -1.5678879053053274, .sampleWeight = 0.0520280112620429 },
	{ .sample = -1.1997100902860450, .sampleWeight = 0.0601091352703015 },
	{ .sample = -0.9205473016275229, .sampleWeight = 0.0663526532241763 },
	{ .sample = -0.6859608829556935, .sampleWeight = 0.0686569819948156 },
	{ .sample = -0.4772650338604341, .sampleWeight = 0.0714941307381180 },
	{ .sample = -0.2817093825097764, .sampleWeight = 0.0732557829230397 },
	{ .sample = -0.0931705533484249, .sampleWeight = 0.0741243625023456 },
	{ .sample = 0.0931705533484249,  .sampleWeight = 0.0741243625023456 },
	{ .sample = 0.2817093825097764,  .sampleWeight = 0.0732557829230397 },
	{ .sample = 0.4772650338604341,  .sampleWeight = 0.0714941307381180 },
	{ .sample = 0.6859608829556935,  .sampleWeight = 0.0686569819948156 },
	{ .sample = 0.9205473016275229,  .sampleWeight = 0.0663526532241763 },
	{ .sample = 1.1997100902860450,  .sampleWeight = 0.0601091352703015 },
	{ .sample = 1.5678879053053274,  .sampleWeight = 0.0520280112620429 },
	{ .sample = 2.2194097942437231,  .sampleWeight = 0.0339789420851602 },
};


/*
 * Helper functions
 */

SignaloidSoCCommand
waitForCommand(void)
{
	SignaloidSoCCommand command = kCalculateNoCommand;

	/*
	 *	Set status to "waitingForCommand"
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusWaitingForCommand);

	/*
	 *	Block until command is issued
	 */
	while (command == kCalculateNoCommand)
	{
		command = C0HALGetCommandRegister();
	}

	return command;
}

void
waitForIdle(void)
{
	/*
	 *	Block until command is cleared
	 */
	while (C0HALGetCommandRegister() != kCalculateNoCommand) {}
}

uint32_t
loadFloatOrUxBinary(volatile uint8_t * buffer, float * value)
{
	union
	{
		float       float32;
		uint32_t    uint32;
		uint8_t     byte[4];
	}
	u;

	u.byte[0]   = buffer[0];
	u.byte[1]   = buffer[1];
	u.byte[2]   = buffer[2];
	u.byte[3]   = buffer[3];
	buffer      += sizeof(uint32_t);

	uint32_t length = u.uint32;
	if (length == 4)
	{
		u.byte[0]   = buffer[0];
		u.byte[1]   = buffer[1];
		u.byte[2]   = buffer[2];
		u.byte[3]   = buffer[3];

		*value = UxHwFloatGaussDist(u.float32, 0.1);
	}
	else
	{
		*value = UxHwFloatByteArrayToDistribution((uint8_t *) buffer, length);
	}

	return length + sizeof(uint32_t);
}

uint32_t
writeUxBinary(float result, volatile uint8_t * buffer, uint32_t bufferBytes)
{
	if (bufferBytes <= sizeof(uint32_t))
	{
		return 0;
	}

	ssize_t resultSize = UxHwFloatDistributionToByteArray(
		result,
		((uint8_t *) buffer) + sizeof(uint32_t),
		bufferBytes - sizeof(uint32_t)
	);

	if (resultSize < 0)
	{
		*((uint32_t *) buffer) = 0;
		return sizeof(uint32_t);
	}

	*((uint32_t *) buffer) = (uint32_t) resultSize;

	return sizeof(uint32_t) + (uint32_t) resultSize;
}


/*
 * Application Logic
 */

void
handleOperations(SignaloidSoCCommand command)
{
	float   inputDistributionA;
	float   inputDistributionB;
	float   result;

	/*
	 *	Set status to inform host that calculation will start
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusCalculating);

	/*
	 *	Turn on status LED
	 */
	C0HALSetLed(true);

	/*
	 *	Create distributional values from inputs
	 */
	if (kC0HALInputBufferUint32[0] != 2)
	{
		/* Error: Not enough input arguments */

		/*
		 * Pack no results
		 */
		kC0HALOutputBufferUint32[0] = 0;

		/*
		 *	Set status to inform host that calculation has finished
		 */
		C0HALSetStatusRegister(kSignaloidSoCStatusDone);

		/*
		 *	Turn off status LED
		 */
		C0HALSetLed(false);
		return;
	}

	volatile uint8_t * inputBuffer = kC0HALInputBufferUint8 + sizeof(uint32_t);
	inputBuffer += loadFloatOrUxBinary(
		inputBuffer,
		&inputDistributionA
	);

	inputBuffer += loadFloatOrUxBinary(
		inputBuffer,
		&inputDistributionB
	);

	/*
	 *	Calculate
	 */
	switch (command)
	{
		case kCalculateAddition:
			result = inputDistributionA + inputDistributionB;
			break;

		case kCalculateSubtraction:
			result = inputDistributionA - inputDistributionB;
			break;

		case kCalculateMultiplication:
			result = inputDistributionA * inputDistributionB;
			break;

		case kCalculateDivision:
			result = inputDistributionA / inputDistributionB;
			break;

		default:
			break;
	}

	/*
	 *	Pack result
	 */
	kC0HALOutputBufferUint32[0] = 1;  /* Pack one value in the following buffer */
	volatile uint8_t *  outputBuffer    = kC0HALOutputBufferUint8 + sizeof(uint32_t);
	const uint8_t *     outputBufferEnd = ((const uint8_t *) kC0HALOutputBufferUint8) + kC0HALOutputBufferUint8Length;
	outputBuffer += writeUxBinary(
		result,
		outputBuffer,
		outputBufferEnd - outputBuffer
	);

	/*
	 *	Turn off status LED
	 */
	C0HALSetLed(false);

	/*
	 *	Set status
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusDone);
}

void
handleSampling(void)
{
	float generatedDistribution = UxHwFloatDistFromWeightedSamples(weightedSamples, kWeightedSampleCount);

	/*
	 *	Set status to inform host that calculation will start
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusCalculating);

	/*
	 *	Turn on status LED
	 */
	C0HALSetLed(true);


	if (kC0HALInputBufferUint32[0] != 1 || kC0HALInputBufferUint32[1] != 4)
	{
		/* Error: Not enough input arguments */

		/*
		 * Pack no results
		 */
		kC0HALOutputBufferUint32[0] = 0;

		/*
		 *	Set status to inform host that calculation has finished
		 */
		C0HALSetStatusRegister(kSignaloidSoCStatusDone);

		/*
		 *	Turn off status LED
		 */
		C0HALSetLed(false);
		return;
	}

	UxHwFloatSampleBatch(generatedDistribution, (float *) kC0HALOutputBufferFloat, kC0HALInputBufferUint32[2]);

	/*
	 *	Turn off status LED
	 */
	C0HALSetLed(false);

	/*
	 *	Set status
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusDone);
}

void
handleCommand(SignaloidSoCCommand command)
{
	switch (command)
	{
		/*
		 *	All of the following commands parse the inputs in the same way
		 */
		case kCalculateAddition:
		case kCalculateSubtraction:
		case kCalculateMultiplication:
		case kCalculateDivision:
			handleOperations(command);
			break;

		case kCalculateSample:
			handleSampling();
			break;

		default:
			C0HALSetStatusRegister(kSignaloidSoCStatusInvalidCommand);
			break;
	}
}

void
setup(void)
{
	C0HALSetLed(false);
	C0HALSetStatusRegister(kSignaloidSoCStatusWaitingForCommand);
}

void
loop(void)
{
	SignaloidSoCCommand command = waitForCommand();
	handleCommand(command);
	waitForIdle();
}

int
main(void)
{
	setup();
	while (1)
	{
		loop();
	}
}
